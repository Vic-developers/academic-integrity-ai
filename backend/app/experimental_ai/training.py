"""Small deterministic logistic baseline and held-out Platt calibration using CPU stdlib.

Only offline research artifacts; never loaded by the document API or approved automatically.
"""

import hashlib
import math
from collections import defaultdict
from pathlib import Path
from app.experimental_ai.corpus import canonical, validate
from app.experimental_ai.features import FEATURES, VERSION, measure

ALGORITHM = "standardized-logistic-l2-platt-v1"


def sigmoid(value):
    return 1 / (1 + math.exp(-max(-40, min(40, value))))


def fit(x, y, *, steps=400, learning_rate=0.1, l2=0.01):
    w = [0.0] * len(x[0])
    bias = 0.0
    for _ in range(steps):
        errors = [sigmoid(sum(a * b for a, b in zip(row, w)) + bias) - label for row, label in zip(x, y)]
        w = [
            weight - learning_rate * (sum(e * row[j] for e, row in zip(errors, x)) / len(x) + l2 * weight)
            for j, weight in enumerate(w)
        ]
        bias -= learning_rate * sum(errors) / len(x)
    return w, bias


def wilson(positive, total):
    if not total:
        return None
    z = 1.959963984540054
    p = positive / total
    den = 1 + z * z / total
    mid = (p + z * z / (2 * total)) / den
    delta = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return [max(0, mid - delta), min(1, mid + delta)]


def metrics(labels, probabilities):
    tp = fp = tn = fn = 0
    for y, p in zip(labels, probabilities):
        if y == 1 and p >= 0.5:
            tp += 1
        elif y == 0 and p >= 0.5:
            fp += 1
        elif y == 0:
            tn += 1
        else:
            fn += 1
    count = len(labels)
    if not count:
        return {"count": 0, "not_assessed": True}
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    ece = 0.0
    bins = []
    for b in range(10):
        indices = [i for i, p in enumerate(probabilities) if min(9, int(p * 10)) == b]
        if not indices:
            continue
        mean_p = sum(probabilities[i] for i in indices) / len(indices)
        frequency = sum(labels[i] for i in indices) / len(indices)
        ece += len(indices) / count * abs(mean_p - frequency)
        bins.append(
            {
                "lower": b / 10,
                "upper": (b + 1) / 10,
                "count": len(indices),
                "mean_model_output": mean_p,
                "observed_positive_frequency": frequency,
            }
        )
    return {
        "count": count,
        "threshold": 0.5,
        "positive_label": "ai",
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "precision": precision,
        "recall": recall,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
        "fpr_wilson_95": wilson(fp, fp + tn),
        "brier": sum((p - y) ** 2 for p, y in zip(probabilities, labels)) / count,
        "ece_10": ece,
        "calibration_bins": bins,
    }


def train(data):
    corpus = validate(data)
    rows = data["samples"]
    vectors = {}
    for row in rows:
        values = measure(row["text"])["values"]
        vectors[row["id"]] = [values[f] for f in FEATURES]
    training = [r for r in rows if r["split"] == "train"]
    raw = [vectors[r["id"]] for r in training]
    means = [sum(row[j] for row in raw) / len(raw) for j in range(len(FEATURES))]
    scales = [math.sqrt(sum((row[j] - means[j]) ** 2 for row in raw) / len(raw)) or 1.0 for j in range(len(FEATURES))]

    def scaled(row):
        return [(v - m) / s for v, m, s in zip(vectors[row["id"]], means, scales)]

    w, b = fit([scaled(r) for r in training], [int(r["label"] == "ai") for r in training])

    def logit(r):
        return sum(a * c for a, c in zip(scaled(r), w)) + b

    calibration = [r for r in rows if r["split"] == "calibration"]
    cw, cb = fit([[logit(r)] for r in calibration], [int(r["label"] == "ai") for r in calibration], steps=300, l2=0.01)
    params = {
        "schema": "experimental-authorship-baseline-v1",
        "algorithm": ALGORITHM,
        "feature_version": VERSION,
        "features": list(FEATURES),
        "means": means,
        "scales": scales,
        "weights": w,
        "bias": b,
        "platt_slope": cw[0],
        "platt_intercept": cb,
        "hyperparameters": {
            "training_steps": 400,
            "calibration_steps": 300,
            "learning_rate": 0.1,
            "l2": 0.01,
            "decision_threshold": 0.5,
        },
        "runtime_policy": "research_only_never_document_authorship_verdict",
        "approved": False,
    }
    report = {}
    for split in ["validation", "calibration", "test"]:
        samples = [r for r in rows if r["split"] == split and r["label"] in {"human", "ai"}]
        ys = [int(r["label"] == "ai") for r in samples]
        raw_p = [sigmoid(logit(r)) for r in samples]
        cal_p = [sigmoid(cw[0] * logit(r) + cb) for r in samples]
        subgroups = defaultdict(list)
        for i, r in enumerate(samples):
            for name in ["language", "domain", "generator"]:
                subgroups[name + ":" + r[name]].append(i)
        report[split] = {
            "uncalibrated": metrics(ys, raw_p),
            "platt_calibrated": metrics(ys, cal_p),
            "by_group": {
                name: metrics([ys[i] for i in indices], [cal_p[i] for i in indices])
                for name, indices in sorted(subgroups.items())
            },
            "excluded_mixed_or_edited": sum(r["split"] == split and r["label"] in {"mixed", "edited"} for r in rows),
        }
    params_hash = hashlib.sha256(canonical(params)).hexdigest()
    report["deployment"] = {
        "approved": False,
        "document_authorship_output": "not_conclusive",
        "document_abstention_rate": 1.0,
        "research_outputs_are_not_authorship_probabilities": True,
        "reasons": ["no_independent_institutional_approval", "no_representative_scientific_validation"]
        + (["technical_fixture_not_real_authorship_data"] if corpus["purpose"] == "technical_fixture" else []),
    }
    manifest = {
        "schema": "experimental-authorship-experiment-v1",
        "corpus": corpus,
        "algorithm": ALGORITHM,
        "feature_version": VERSION,
        "model_sha256": params_hash,
        "report_sha256": hashlib.sha256(canonical(report)).hexdigest(),
        "approved": False,
        "hardware_requirement": "CPU only",
        "dependencies": "Python standard library",
        "source_code_sha256": {
            name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ["features.py", "corpus.py", "training.py"]
        },
    }
    manifest["experiment_id"] = hashlib.sha256(canonical(manifest)).hexdigest()
    return {"manifest": manifest, "model": params, "report": report}

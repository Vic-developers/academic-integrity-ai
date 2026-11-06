"""Metrics and actual CPU training on declared technical patterns, not detector accuracy."""

import copy
import importlib.util
import math
from pathlib import Path
import pytest
from app.experimental_ai.features import measure, tokens
from app.experimental_ai.corpus import validate
from app.experimental_ai.training import metrics, train, wilson
from conftest import login
from test_literal import extracted


def fixture_corpus():
    path = Path(__file__).resolve().parents[2] / "evaluation/experimental-ai-v1/technical_fixture.py"
    spec = importlib.util.spec_from_file_location("technical_patterns", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.corpus()


def test_observables_counts_empty_and_repetition_without_verdict():
    empty = measure("")
    assert empty["counts"]["tokens"] == 0
    assert all(v == 0 for v in empty["values"].values())
    result = measure("uno dos tres uno dos tres.")
    assert result["counts"]["tokens"] == 6 and result["counts"]["distinct_tokens"] == 3
    assert result["values"]["hapax_ratio"] == 0
    assert result["values"]["repeated_trigram_ratio"] == 0.25
    assert result["values"]["mattr_50"] == 0.5
    assert result["authorship_probability"] is None and result["assessment"] == "not_conclusive"
    assert all(math.isfinite(v) for v in result["values"].values())


def test_unicode_decimal_and_moving_window():
    assert tokens("ÁRBOL árbol ﬁ ß 🧭") == ["árbol", "árbol", "fi", "ss"]
    assert measure("La cifra es 12.5 puntos. Otro resultado.")["counts"]["sentences"] == 2
    text = " ".join(["alfa"] * 50 + ["beta"] * 50)
    r = measure(text)
    brute = sum(len(set(tokens(text)[i : i + 50])) / 50 for i in range(51)) / 51
    assert r["values"]["mattr_50"] == pytest.approx(brute)
    assert "text_below_100_tokens" not in r["abstention_reasons"]
    with pytest.raises(ValueError, match="linguistic_text_budget"):
        measure("x" * 500001)


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("training_allowed", False, "corpus_authorization"),
        ("evaluation_allowed", False, "corpus_authorization"),
        ("personal_data_reviewed", False, "corpus_authorization"),
        ("license", "", "corpus_provenance"),
        ("purpose", "production", "corpus_purpose"),
    ],
)
def test_corpus_requires_explicit_provenance_and_authorization(field, value, error):
    data = fixture_corpus()
    data[field] = value
    with pytest.raises(ValueError, match=error):
        validate(data)


@pytest.mark.parametrize("field", ["author_id", "source_id", "prompt_id", "document_id"])
def test_split_groups_cannot_leak(field):
    data = fixture_corpus()
    data["samples"][12][field] = data["samples"][0][field]
    with pytest.raises(ValueError, match="cross_split_group_leakage"):
        validate(data)


def test_exact_and_template_duplicates_fail_closed():
    data = fixture_corpus()
    data["samples"][12]["text"] = data["samples"][0]["text"].upper()
    with pytest.raises(ValueError, match="duplicate_normalized_text"):
        validate(data)
    data = fixture_corpus()
    data["samples"][12]["text"] += " " + data["samples"][0]["text"]
    with pytest.raises(ValueError, match="cross_split_shared_eight_tokens"):
        validate(data)


def test_splits_require_both_labels_and_reject_ambiguous_training():
    data = fixture_corpus()
    data["samples"][0]["label"] = "mixed"
    with pytest.raises(ValueError, match="nonbinary_training_or_calibration_label"):
        validate(data)
    data = fixture_corpus()
    data["samples"] = [r for r in data["samples"] if not (r["split"] == "test" and r["label"] == "human")]
    with pytest.raises(ValueError, match="insufficient_binary_split"):
        validate(data)


def test_cpu_training_reproducible_and_never_approved():
    data = fixture_corpus()
    one = train(data)
    two = train(copy.deepcopy(data))
    assert one == two
    assert not one["manifest"]["approved"] and not one["model"]["approved"]
    assert one["manifest"]["corpus"]["purpose"] == "technical_fixture"
    assert one["report"]["test"]["platt_calibrated"]["count"] == 12
    assert "technical_fixture_not_real_authorship_data" in one["report"]["deployment"]["reasons"]
    assert len(one["manifest"]["experiment_id"]) == 64
    assert all(math.isfinite(v) for v in one["model"]["weights"])
    # Held-out test changes must not fit scaling, coefficients or Platt calibration.
    changed = copy.deepcopy(data)
    for row in changed["samples"]:
        if row["split"] == "test":
            row["text"] += " añadidura exclusivamente experimental"
    other = train(changed)
    assert other["model"] == one["model"]
    assert other["manifest"]["experiment_id"] != one["manifest"]["experiment_id"]


def test_metric_denominators_intervals_and_calibration_bins():
    result = metrics([0, 0, 1, 1], [0.1, 0.8, 0.9, 0.4])
    assert result["confusion"] == {"tp": 1, "fp": 1, "tn": 1, "fn": 1}
    assert result["false_positive_rate"] == 0.5 and result["f1"] == 0.5
    assert result["brier"] == pytest.approx((0.01 + 0.64 + 0.01 + 0.36) / 4)
    assert sum(b["count"] for b in result["calibration_bins"]) == 4
    assert wilson(0, 0) is None
    assert wilson(0, 2)[1] > 0.5  # Tiny samples cannot establish a low false positive rate.
    assert metrics([1], [0.1])["precision"] is None
    assert metrics([], [])["not_assessed"]


def test_observation_api_permissions_provenance_no_training_and_delete(client, seed):
    login(client, tenant=seed["a"])
    content = "🧭 Texto sintético de prueba. Una frase repetida. Una frase repetida."
    document = extracted(client, "observacion.txt", content)
    path = "/api/v1/experimental-ai/documents/" + document["id"]
    result = client.get(path)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["observation"] == measure(content)
    assert body["document"]["document_id"] == document["id"]
    assert not body["trained_on_this_document"] and body["model"] is None
    caps = client.get("/api/v1/experimental-ai/capabilities").json()
    assert not caps["authorship_classifier_available"] and not caps["document_training_allowed"]
    login(client, user="teacher", tenant=seed["a"])
    assert client.get(path).status_code == 404
    login(client, user="outsider", tenant=seed["b"])
    assert client.get(path).status_code == 404
    login(client, tenant=seed["a"])
    assert client.delete("/api/v1/documents/" + document["id"]).status_code == 204
    assert client.get(path).status_code == 404


def test_student_observations_remain_inconclusive(client, seed):
    login(client, user="student", tenant=seed["a"])
    doc = extracted(client, "propio.txt", "Palabras propias de una prueba técnica autorizada.")
    r = client.get("/api/v1/experimental-ai/documents/" + doc["id"])
    assert r.status_code == 200
    assert r.json()["observation"]["assessment"] == "not_conclusive"
    assert r.json()["observation"]["authorship_probability"] is None


def test_logistic_optimizer_learns_a_known_separable_problem():
    from app.experimental_ai.training import fit, sigmoid

    w, b = fit([[-2], [-1], [1], [2]], [0, 0, 1, 1])
    assert sigmoid(w[0] * 2 + b) > 0.9
    assert sigmoid(-w[0] * 2 + b) < 0.1


def test_cli_artifacts_match_manifest_and_are_immutable(tmp_path):
    import hashlib
    import json

    script = Path(__file__).resolve().parents[2] / "scripts/train_experimental_ai.py"
    spec = importlib.util.spec_from_file_location("offline_training_cli", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "private-corpus.json"
    path.write_text(json.dumps(fixture_corpus()))
    output = tmp_path / "experiments"
    folder, identity = module.run(path, output)
    manifest = json.loads((folder / "manifest.json").read_text())
    assert folder.name == identity
    assert hashlib.sha256((folder / "model.json").read_bytes().rstrip(b"\n")).hexdigest() == manifest["model_sha256"]
    assert hashlib.sha256((folder / "report.json").read_bytes().rstrip(b"\n")).hexdigest() == manifest["report_sha256"]
    assert (folder / "model.json").stat().st_mode & 0o777 == 0o600
    assert not any(p.suffix in {".pkl", ".pickle", ".joblib"} for p in folder.iterdir())
    with pytest.raises(FileExistsError):
        module.run(path, output)
    path.write_text('{"unknown": NaN}')
    with pytest.raises(ValueError, match="non_finite_json"):
        module.run(path, output)


def test_ambiguous_test_data_excluded_from_binary_accuracy():
    data = fixture_corpus()
    row = copy.deepcopy(data["samples"][-1])
    for field in ["id", "document_id", "author_id", "source_id", "prompt_id"]:
        row[field] = "mixed-extra"
    row["label"] = "mixed"
    row["text"] = "Un texto mixto de prueba técnica con contenido inventado para evaluar solamente la abstención."
    data["samples"].append(row)
    result = train(data)
    assert result["report"]["test"]["excluded_mixed_or_edited"] == 1
    assert result["report"]["test"]["platt_calibrated"]["count"] == 12
    assert result["report"]["deployment"]["document_authorship_output"] == "not_conclusive"

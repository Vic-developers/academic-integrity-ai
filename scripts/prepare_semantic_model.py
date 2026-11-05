"""Download a pinned, data-only CPU candidate. Never activate an unevaluated model."""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ARTIFACT = "Xenova/paraphrase-multilingual-MiniLM-L12-v2"
ALLOWED_LICENSES = {"apache-2.0", "mit", "bsd-3-clause"}
MAX_FILE_BYTES = 256 * 1024 * 1024


def allowed_url(url):
    p = urllib.parse.urlsplit(url)
    host = p.hostname or ""
    return (
        p.scheme == "https"
        and not p.username
        and not p.password
        and p.port in {None, 443}
        and (host == "huggingface.co" or host.endswith((".huggingface.co", ".hf.co")))
    )


class ModelRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise ValueError("Unapproved model download destination")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url):
    if not allowed_url(url):
        raise ValueError("Unapproved model metadata destination")
    return urllib.request.build_opener(ModelRedirects()).open(url, timeout=60)


def metadata(repo):
    with open_url(f"https://huggingface.co/api/models/{repo}?blobs=true") as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Oversized model metadata")
    value = json.loads(raw)
    revision = value.get("sha", "")
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Immutable upstream revision unavailable")
    license_id = value.get("cardData", {}).get("license", "")
    if license_id not in ALLOWED_LICENSES:
        raise ValueError("Model license requires explicit review")
    return value, license_id


def download(repo, revision, remote, target, expected_sha=None):
    url = f"https://huggingface.co/{repo}/resolve/{revision}/{remote}"
    digest = hashlib.sha256()
    count = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with open_url(url) as response, target.open("xb") as output:
        while data := response.read(1024 * 1024):
            count += len(data)
            if count > MAX_FILE_BYTES:
                raise ValueError("Model artifact exceeds size budget")
            output.write(data)
            digest.update(data)
    value = digest.hexdigest()
    if expected_sha is not None and value != expected_sha:
        raise ValueError("Model artifact checksum mismatch")
    target.chmod(0o444)
    return {
        "sha256": value,
        "bytes": count,
        "upstream_path": remote,
        "repository": repo,
        "revision": revision,
    }


def prepare(output):
    base, base_license = metadata(BASE)
    artifact, artifact_license = metadata(ARTIFACT)
    revision = artifact["sha"]
    entries = {s["rfilename"]: s for s in artifact.get("siblings", [])}
    expected = entries.get("onnx/model_quantized.onnx", {}).get("lfs", {}).get("sha256")
    if not expected or len(expected) != 64:
        raise ValueError(
            "Pinned ONNX artifact SHA-256 unavailable from upstream metadata"
        )
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    destination = output / ("multilingual-minilm-q8-" + revision[:12])
    if destination.exists():
        raise ValueError(
            "Model version already exists; verify it instead of replacing it"
        )
    staging = Path(tempfile.mkdtemp(prefix=".candidate-", dir=output))
    try:
        files = {}
        for local, remote in [
            ("model.onnx", "onnx/model_quantized.onnx"),
            ("tokenizer.json", "tokenizer.json"),
            ("tokenizer_config.json", "tokenizer_config.json"),
            ("config.json", "config.json"),
            ("README.md", "README.md"),
        ]:
            files[local] = download(
                ARTIFACT,
                revision,
                remote,
                staging / local,
                expected if local == "model.onnx" else None,
            )
        for local, remote in [
            ("base-model-card.md", "README.md"),
            ("pooling.json", "1_Pooling/config.json"),
            ("sentence_bert_config.json", "sentence_bert_config.json"),
        ]:
            files[local] = download(BASE, base["sha"], remote, staging / local)
        pooling = json.loads((staging / "pooling.json").read_text())
        if not pooling.get("pooling_mode_mean_tokens") or any(
            v
            for k, v in pooling.items()
            if k.startswith("pooling_mode_") and k != "pooling_mode_mean_tokens"
        ):
            raise ValueError(
                "Unexpected pooling; candidate needs a reviewed encoder implementation"
            )
        config = json.loads((staging / "config.json").read_text())
        max_tokens = json.loads((staging / "sentence_bert_config.json").read_text())[
            "max_seq_length"
        ]
        if config.get("hidden_size") != 384 or not 16 <= max_tokens <= 512:
            raise ValueError("Unexpected model dimension or sequence budget")
        manifest = {
            "schema": "semantic-bundle-v1",
            "base_model": BASE,
            "base_revision": base["sha"],
            "artifact_model": ARTIFACT,
            "revision": revision,
            "licenses": {"base": base_license, "artifact": artifact_license},
            "dimension": 384,
            "max_tokens": max_tokens,
            "pooling": "attention-mask-mean-l2",
            "provider": "CPUExecutionProvider",
            "files": files,
            "approved": False,
            "evaluation": None,
        }
        manifest["model_key"] = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (staging / "manifest.json").chmod(0o444)
        os.replace(staging, destination)
        return destination
    finally:
        if staging.exists():
            shutil.rmtree(staging)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="models/cache")
    args = parser.parse_args()
    try:
        path = prepare(args.output_dir)
        print("Candidate artifacts pinned and verified:", path)
        print("Not activated: independent calibration and evaluation are required.")
    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        # Never print signed CDN URLs, proxy values or credential-bearing request objects.
        reason = (
            "model_source_network_unavailable"
            if isinstance(exc, (urllib.error.URLError, TimeoutError))
            else "model_artifact_verification_failed"
        )
        print(reason)
        raise SystemExit(2) from None

"""Technical preparation only: no fake embeddings or claimed semantic accuracy."""

import hashlib
import importlib.util
import json
from pathlib import Path
import urllib.error
import pytest
from app.semantic.chunking import passages
from app.semantic.encoder import EvaluationEncoder
from conftest import login
from app.semantic.registry import ModelUnavailable, verify_bundle

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("semantic_installer", ROOT / "scripts/prepare_semantic_model.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def test_candidate_explicitly_not_approved_and_has_no_invented_revision(client, seed):
    candidate = json.loads((ROOT / "models/semantic-candidate.json").read_text())
    assert candidate["approved"] is False
    assert candidate["revision"] is None and candidate["sha256"] is None and candidate["evaluation"] is None
    login(client, tenant=seed["a"])
    capabilities = client.get("/api/v1/audits/capabilities").json()
    assert capabilities["semantic_available"] is False


def bundle(root):
    root.mkdir()
    names = [
        "model.onnx",
        "tokenizer.json",
        "config.json",
        "tokenizer_config.json",
        "pooling.json",
        "sentence_bert_config.json",
        "README.md",
        "base-model-card.md",
    ]
    files = {}
    for name in names:
        data = ("TECHNICAL HASH FIXTURE, NOT A MODEL: " + name).encode()
        (root / name).write_bytes(data)
        files[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    manifest = {
        "schema": "semantic-bundle-v1",
        "dimension": 384,
        "pooling": "attention-mask-mean-l2",
        "provider": "CPUExecutionProvider",
        "max_tokens": 128,
        "files": files,
        "licenses": {"base": "apache-2.0", "artifact": "apache-2.0"},
        "approved": False,
        "evaluation": None,
    }
    manifest["model_key"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest))
    return manifest


def test_bundle_checks_bytes_and_refuses_activation_without_evaluation(tmp_path):
    root = tmp_path / "model"
    manifest = bundle(root)
    assert verify_bundle(root, require_approval=False)["model_key"] == manifest["model_key"]
    with pytest.raises(ModelUnavailable, match="not_evaluated"):
        verify_bundle(root)
    manifest.update(approved=True, evaluation={"status": "untrusted flag"})
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ModelUnavailable, match="activation_pending_evaluation"):
        verify_bundle(root)
    (root / "model.onnx").write_bytes(b"corrupt")
    with pytest.raises(ModelUnavailable, match="artifact_invalid"):
        verify_bundle(root, require_approval=False)


def test_checksum_corruption_same_length_and_symlink_are_rejected(tmp_path):
    root = tmp_path / "model"
    bundle(root)
    path = root / "tokenizer.json"
    raw = path.read_bytes()
    path.write_bytes(b"X" + raw[1:])
    with pytest.raises(ModelUnavailable, match="checksum_mismatch"):
        verify_bundle(root, require_approval=False)
    path.unlink()
    (tmp_path / "outside").write_bytes(raw)
    path.symlink_to(tmp_path / "outside")
    with pytest.raises(ModelUnavailable, match="artifact_invalid"):
        verify_bundle(root, require_approval=False)


def test_extra_files_or_traversal_in_manifest_never_opened(tmp_path):
    root = tmp_path / "model"
    m = bundle(root)
    m["files"]["../outside"] = m["files"].pop("README.md")
    identity = {k: v for k, v in m.items() if k != "model_key"}
    m["model_key"] = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (root / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ModelUnavailable, match="file_set_invalid"):
        verify_bundle(root, require_approval=False)


def test_model_redirects_stay_on_https_distribution_hosts():
    assert installer.allowed_url("https://huggingface.co/model/resolve/revision/file")
    assert installer.allowed_url("https://cas-bridge.xethub.hf.co/file?signature=synthetic")
    for value in [
        "http://huggingface.co/file",
        "https://huggingface.co.attacker.example/file",
        "https://user:pass@huggingface.co/file",
        "https://huggingface.co:8443/file",
        "https://127.0.0.1/file",
        "file:///etc/passwd",
    ]:
        assert not installer.allowed_url(value)


def test_network_failure_precedes_output_creation_and_does_not_replace_data(tmp_path, monkeypatch):
    root = tmp_path / "models"

    def denied(*args):
        raise urllib.error.URLError("synthetic network denial")

    monkeypatch.setattr(installer, "metadata", denied)
    with pytest.raises(urllib.error.URLError):
        installer.prepare(root)
    assert not root.exists()


def test_failed_download_rolls_back_staging_only(tmp_path, monkeypatch):
    root = tmp_path / "models"
    root.mkdir()
    (root / "keep.txt").write_text("existing user data")
    metadata = {"sha": "a" * 40, "siblings": [{"rfilename": "onnx/model_quantized.onnx", "lfs": {"sha256": "b" * 64}}]}
    monkeypatch.setattr(installer, "metadata", lambda repo: (metadata, "apache-2.0"))

    def corrupt(repo, rev, remote, target, expected):
        target.write_bytes(b"partial")
        raise ValueError("checksum mismatch")

    monkeypatch.setattr(installer, "download", corrupt)
    with pytest.raises(ValueError):
        installer.prepare(root)
    assert sorted(p.name for p in root.iterdir()) == ["keep.txt"]
    assert (root / "keep.txt").read_text() == "existing user data"


def test_unicode_original_ranges_and_token_budgets_are_not_normalized_offsets():
    value = (
        "🧭 Árbol ß ﬁ uno dos tres cuatro cinco seis siete ocho. Nueve diez once doce trece catorce quince dieciséis."
    )
    result = passages(value, lambda text: len(text.split()) + 2, 14, min_words=8)
    assert result["passages"]
    for chunk in result["passages"]:
        assert value[chunk["start"] : chunk["end"]] == chunk["text"]
        assert chunk["tokens"] <= 14
    assert "Árbol ß ﬁ" in result["passages"][0]["text"]


def test_long_sentences_overlap_and_oversized_words_abstain():
    value = " ".join("palabra" + str(i) for i in range(60))
    result = passages(value, lambda text: len(text.split()) + 2, 18, min_words=8)
    assert len(result["passages"]) > 1
    assert result["passages"][1]["start"] < result["passages"][0]["end"]
    assert max(c["tokens"] for c in result["passages"]) <= 18
    oversized = passages("x" * 100, lambda text: len(text), 10, min_words=1)
    assert oversized["passages"] == [] and oversized["coverage"] == "partial"
    assert oversized["skipped"][0]["reason"] == "word_exceeds_token_budget"


def test_small_text_and_passage_budget_remain_explicit():
    assert passages("muy corto", lambda text: len(text.split()), 16)["coverage"] == "partial"
    text = " ".join("palabra" + str(i) for i in range(80))
    result = passages(text, lambda text: len(text.split()), 12, max_passages=1)
    assert len(result["passages"]) == 1
    assert any(s["reason"] == "passage_budget" for s in result["skipped"])
    with pytest.raises(ValueError):
        passages("x" * 100001, len, 128)


def test_encoder_refuses_missing_model_before_import_or_download(tmp_path):
    with pytest.raises(ModelUnavailable, match="model_manifest_unavailable"):
        EvaluationEncoder(tmp_path / "missing")

"""Verify local, immutable, data-only model bundles before any inference."""

import hashlib
import json
from pathlib import Path


class ModelUnavailable(RuntimeError):
    pass


def verify_bundle(directory: Path, *, require_approval=True) -> dict:
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    if directory.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise ModelUnavailable("model_manifest_unavailable")
    try:
        if manifest_path.stat().st_size > 64 * 1024:
            raise ModelUnavailable("model_manifest_invalid")
        manifest = json.loads(manifest_path.read_text())
        if (
            manifest["schema"] != "semantic-bundle-v1"
            or manifest["dimension"] != 384
            or manifest["pooling"] != "attention-mask-mean-l2"
            or manifest["provider"] != "CPUExecutionProvider"
            or not 16 <= manifest["max_tokens"] <= 512
        ):
            raise ModelUnavailable("model_identity_not_supported")
        if require_approval and (not manifest.get("approved") or not manifest.get("evaluation")):
            raise ModelUnavailable("model_not_evaluated")
        identity = {k: v for k, v in manifest.items() if k not in {"model_key", "approved", "evaluation"}}
        identity.update(approved=False, evaluation=None)
        key = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if manifest.get("model_key") != key:
            raise ModelUnavailable("model_identity_mismatch")
        files = manifest["files"]
        required = {
            "model.onnx",
            "tokenizer.json",
            "config.json",
            "tokenizer_config.json",
            "pooling.json",
            "sentence_bert_config.json",
            "README.md",
            "base-model-card.md",
        }
        if not isinstance(files, dict) or set(files) != required:
            raise ModelUnavailable("model_file_set_invalid")
        if (
            any(
                not isinstance(item.get("bytes"), int) or not 0 < item["bytes"] <= 256 * 1024 * 1024
                for item in files.values()
            )
            or sum(item["bytes"] for item in files.values()) > 320 * 1024 * 1024
        ):
            raise ModelUnavailable("model_artifact_size_invalid")
        for filename, item in files.items():
            path = directory / filename
            if (
                path.is_symlink()
                or not path.is_file()
                or path.resolve().parent != directory.resolve()
                or path.stat().st_size != item["bytes"]
            ):
                raise ModelUnavailable("model_artifact_invalid")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != item["sha256"]:
                raise ModelUnavailable("model_checksum_mismatch")
        if any(
            license_id not in {"apache-2.0", "mit", "bsd-3-clause"} for license_id in manifest["licenses"].values()
        ) or set(manifest["licenses"]) != {"base", "artifact"}:
            raise ModelUnavailable("model_license_not_reviewed")
        # Activation is deliberately unavailable until the independent evaluation gate is implemented and passed.
        if require_approval:
            raise ModelUnavailable("model_activation_pending_evaluation")
        return manifest
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ModelUnavailable("model_manifest_invalid") from exc

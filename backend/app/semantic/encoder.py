"""Offline CPU inference for evaluation only; no unverified remote code or model download."""

from pathlib import Path
from app.semantic.registry import ModelUnavailable, verify_bundle


class EvaluationEncoder:
    def __init__(self, directory: Path):
        self.manifest = verify_bundle(directory, require_approval=False)
        try:
            import numpy as np
            import onnxruntime as ort
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise ModelUnavailable("semantic_cpu_dependencies_unavailable") from exc
        self.np = np
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.log_severity_level = 3
        # Load bytes to disallow an ONNX graph from resolving arbitrary external-weight paths.
        self.session = ort.InferenceSession(
            (Path(directory) / "model.onnx").read_bytes(), sess_options=options, providers=["CPUExecutionProvider"]
        )
        if self.session.get_providers() != ["CPUExecutionProvider"]:
            raise ModelUnavailable("cpu_provider_not_exclusive")
        self.tokenizer = Tokenizer.from_file(str(Path(directory) / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.inputs = {i.name for i in self.session.get_inputs()}
        if (
            not self.inputs <= {"input_ids", "attention_mask", "token_type_ids"}
            or not {"input_ids", "attention_mask"} <= self.inputs
        ):
            raise ModelUnavailable("model_input_contract_unsupported")
        if "last_hidden_state" not in {o.name for o in self.session.get_outputs()}:
            raise ModelUnavailable("model_output_contract_unsupported")

    def token_count(self, text: str) -> int:
        return len(self.tokenizer.encode(text).ids)

    def encode(self, texts: list[str]):
        np = self.np
        if not 1 <= len(texts) <= 8:
            raise ValueError("Embedding batches must contain 1–8 passages")
        if any(not text.strip() or len(text) > 4096 for text in texts):
            raise ValueError("Empty or oversized passage")
        encoded = self.tokenizer.encode_batch(texts)
        if any(len(item.ids) > self.manifest["max_tokens"] for item in encoded):
            raise ValueError("Passage exceeds token budget; silent truncation is forbidden")
        width = max(len(item.ids) for item in encoded)
        ids = np.zeros((len(texts), width), dtype=np.int64)
        masks = np.zeros_like(ids)
        types = np.zeros_like(ids)
        pad_id = self.tokenizer.token_to_id("[PAD]")
        if pad_id is None:
            pad_id = self.tokenizer.token_to_id("<pad>")
        if pad_id is None:
            raise ModelUnavailable("tokenizer_padding_contract_unsupported")
        ids.fill(pad_id)
        for i, item in enumerate(encoded):
            ids[i, : len(item.ids)] = item.ids
            masks[i, : len(item.ids)] = item.attention_mask
            types[i, : len(item.ids)] = item.type_ids
        inputs = {"input_ids": ids, "attention_mask": masks, "token_type_ids": types}
        states = self.session.run(["last_hidden_state"], {k: v for k, v in inputs.items() if k in self.inputs})[0]
        if states.shape != (len(texts), width, 384) or not np.isfinite(states).all():
            raise ModelUnavailable("invalid_model_output")
        weighted = states * masks[:, :, None].astype(states.dtype)
        vectors = weighted.sum(axis=1) / np.maximum(masks.sum(axis=1, keepdims=True), 1).astype(states.dtype)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if not np.isfinite(vectors).all() or (norms <= 0).any():
            raise ModelUnavailable("invalid_embedding_vector")
        return vectors / norms

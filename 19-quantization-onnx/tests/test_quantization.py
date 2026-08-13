"""Live tests against the real trained model, real ONNX export, and real
quantization — no mocking. Assumes train_and_export.py has already been
run once (see README) so the ONNX files exist; skips otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from config import FP32_ONNX_PATH, INT8_ONNX_PATH
from train_and_export import load_data, evaluate_onnx


@pytest.fixture(scope="module", autouse=True)
def require_exported_models():
    if not FP32_ONNX_PATH.exists() or not INT8_ONNX_PATH.exists():
        pytest.skip("run train_and_export.py first to produce the ONNX files")


@pytest.fixture(scope="module")
def test_dataset():
    _, test_ds = load_data()
    return test_ds


def test_int8_model_is_smaller_than_fp32(test_dataset):
    fp32_size = FP32_ONNX_PATH.stat().st_size
    int8_size = INT8_ONNX_PATH.stat().st_size
    assert int8_size < fp32_size
    assert int8_size < fp32_size * 0.5  # quantization should be a substantial reduction, not marginal


def test_int8_accuracy_does_not_regress_meaningfully(test_dataset):
    """Quantization can lose accuracy; it should not lose MUCH — a large
    drop would mean the quantization was too aggressive for this model."""
    fp32_stats = evaluate_onnx(FP32_ONNX_PATH, test_dataset)
    int8_stats = evaluate_onnx(INT8_ONNX_PATH, test_dataset)
    accuracy_drop = fp32_stats["accuracy"] - int8_stats["accuracy"]
    assert accuracy_drop < 0.05  # allow up to 5 points of degradation


def test_both_models_produce_valid_probability_shaped_output(test_dataset):
    """Negative/shape-sanity case: both models must output exactly 10
    logits per MNIST digit class for every sample, not a malformed or
    truncated output shape from the export/quantization process."""
    import onnxruntime as ort
    import numpy as np
    from torch.utils.data import DataLoader

    loader = DataLoader(test_dataset, batch_size=8)
    X, _ = next(iter(loader))

    for path in (FP32_ONNX_PATH, INT8_ONNX_PATH):
        session = ort.InferenceSession(str(path))
        outputs = session.run(None, {"input": X.numpy().astype(np.float32)})
        assert outputs[0].shape == (8, 10)

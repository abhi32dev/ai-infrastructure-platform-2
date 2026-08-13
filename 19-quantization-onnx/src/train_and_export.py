"""Trains the small CNN on a real MNIST subset, exports to ONNX (fp32),
then applies dynamic INT8 quantization to a second ONNX file — measuring
file size and accuracy for both, the real tradeoff quantization makes.
"""

import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType
import numpy as np

from config import DATA_DIR, FP32_ONNX_PATH, INT8_ONNX_PATH, EPOCHS, BATCH_SIZE, LR, TRAIN_SUBSET, TEST_SUBSET
from model import SmallCNN


def load_data():
    transform = transforms.ToTensor()
    train_full = datasets.MNIST(root=str(DATA_DIR), train=True, download=True, transform=transform)
    test_full = datasets.MNIST(root=str(DATA_DIR), train=False, download=True, transform=transform)
    train = Subset(train_full, range(TRAIN_SUBSET))
    test = Subset(test_full, range(TEST_SUBSET))
    return train, test


def train_model(train_ds) -> SmallCNN:
    model = SmallCNN()
    loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(1, EPOCHS + 1):
        total_loss = 0.0
        for X, y in loader:
            optimizer.zero_grad()
            logits = model(X)
            loss = loss_fn(logits, y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"epoch {epoch}/{EPOCHS}: avg_loss={total_loss/len(loader):.4f}")

    return model


def export_to_onnx(model: SmallCNN, path):
    model.eval()
    dummy_input = torch.randn(1, 1, 28, 28)
    # dynamo=False: the newer dynamo-based exporter (torch's new default)
    # produced a graph with a shape-inference conflict that broke
    # onnxruntime's quantize_dynamic (a real compatibility snag hit while
    # building this — see README). The legacy TorchScript-based exporter
    # produces a more conventional graph that onnxruntime's quantization
    # tooling handles correctly.
    torch.onnx.export(
        model, dummy_input, str(path),
        input_names=["input"], output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        dynamo=False,
    )


def evaluate_onnx(onnx_path, test_ds) -> dict:
    session = ort.InferenceSession(str(onnx_path))
    loader = DataLoader(test_ds, batch_size=BATCH_SIZE)

    correct = 0
    total = 0
    latencies = []
    for X, y in loader:
        X_np = X.numpy().astype(np.float32)
        start = time.time()
        outputs = session.run(None, {"input": X_np})
        latencies.append(time.time() - start)
        preds = outputs[0].argmax(axis=1)
        correct += (preds == y.numpy()).sum()
        total += len(y)

    return {
        "accuracy": correct / total,
        "avg_batch_latency_sec": sum(latencies) / len(latencies),
        "file_size_bytes": onnx_path.stat().st_size,
    }


def run_full_pipeline():
    train_ds, test_ds = load_data()
    model = train_model(train_ds)
    export_to_onnx(model, FP32_ONNX_PATH)

    quantize_dynamic(str(FP32_ONNX_PATH), str(INT8_ONNX_PATH), weight_type=QuantType.QUInt8)

    fp32_stats = evaluate_onnx(FP32_ONNX_PATH, test_ds)
    int8_stats = evaluate_onnx(INT8_ONNX_PATH, test_ds)

    return fp32_stats, int8_stats


if __name__ == "__main__":
    fp32_stats, int8_stats = run_full_pipeline()

    print(f"\n=== fp32 ONNX ===")
    print(f"  accuracy: {fp32_stats['accuracy']:.4f}")
    print(f"  file size: {fp32_stats['file_size_bytes']:,} bytes")
    print(f"  avg batch latency: {fp32_stats['avg_batch_latency_sec']*1000:.2f}ms")

    print(f"\n=== int8 ONNX (dynamically quantized) ===")
    print(f"  accuracy: {int8_stats['accuracy']:.4f}")
    print(f"  file size: {int8_stats['file_size_bytes']:,} bytes")
    print(f"  avg batch latency: {int8_stats['avg_batch_latency_sec']*1000:.2f}ms")

    size_reduction = (1 - int8_stats['file_size_bytes'] / fp32_stats['file_size_bytes']) * 100
    accuracy_delta = int8_stats['accuracy'] - fp32_stats['accuracy']
    print(f"\nSize reduction: {size_reduction:.1f}% | Accuracy delta: {accuracy_delta:+.4f}")

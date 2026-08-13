from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FP32_ONNX_PATH = Path(__file__).resolve().parent.parent / "model_fp32.onnx"
INT8_ONNX_PATH = Path(__file__).resolve().parent.parent / "model_int8.onnx"

EPOCHS = 2
BATCH_SIZE = 64
LR = 1e-3
TRAIN_SUBSET = 4000   # MNIST subset for a fast local training run
TEST_SUBSET = 1000

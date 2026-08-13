"""Exports the trained Keras model to TFLite — TensorFlow's actual
production differentiator over PyTorch for edge/mobile deployment (named
directly in the market research), distinct from project 19's ONNX/CPU
quantization story. Verifies the TFLite model's predictions match the
original Keras model's predictions on the same inputs, not just that
the conversion didn't raise an exception.
"""

from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow import keras

from train import CHECKPOINT_PATH, load_data

TFLITE_PATH = Path(__file__).resolve().parent.parent / "model.tflite"


def export_to_tflite(model: keras.Model) -> Path:
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    TFLITE_PATH.write_bytes(tflite_model)
    return TFLITE_PATH


def compare_keras_vs_tflite(model: keras.Model, x_test: np.ndarray, n_samples: int = 20) -> dict:
    interpreter = tf.lite.Interpreter(model_path=str(TFLITE_PATH))
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    keras_preds = []
    tflite_preds = []
    for i in range(n_samples):
        sample = x_test[i:i+1].astype("float32")

        keras_pred = model.predict(sample, verbose=0).argmax()
        keras_preds.append(int(keras_pred))

        interpreter.set_tensor(input_details["index"], sample)
        interpreter.invoke()
        tflite_output = interpreter.get_tensor(output_details["index"])
        tflite_preds.append(int(tflite_output.argmax()))

    agreement = sum(k == t for k, t in zip(keras_preds, tflite_preds)) / n_samples

    return {
        "keras_size_bytes": CHECKPOINT_PATH.stat().st_size,
        "tflite_size_bytes": TFLITE_PATH.stat().st_size,
        "prediction_agreement": agreement,
        "n_samples": n_samples,
    }


if __name__ == "__main__":
    _, _, (x_test, y_test) = load_data()
    model = keras.models.load_model(CHECKPOINT_PATH)

    export_to_tflite(model)
    stats = compare_keras_vs_tflite(model, x_test)

    print(f"Keras model size:  {stats['keras_size_bytes']:,} bytes")
    print(f"TFLite model size: {stats['tflite_size_bytes']:,} bytes")
    size_reduction = (1 - stats['tflite_size_bytes'] / stats['keras_size_bytes']) * 100
    print(f"Size reduction: {size_reduction:.1f}%")
    print(f"Keras vs TFLite prediction agreement on {stats['n_samples']} samples: {stats['prediction_agreement']*100:.1f}%")

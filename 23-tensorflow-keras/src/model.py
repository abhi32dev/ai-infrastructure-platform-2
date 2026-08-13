"""Keras CNN, deliberately mirroring project 19's PyTorch CNN
architecture (same conv/pool/dense shape) on the same MNIST task — the
point is a direct, controlled framework comparison, not a different
model. TensorFlow's actual differentiator demonstrated here isn't the
model itself; it's the TFLite mobile/edge export pipeline in
export_tflite.py, since that's TensorFlow's real production strength
over PyTorch (named explicitly in the market research: "dominant for
edge/enterprise/mobile deployment").
"""

from tensorflow import keras
from tensorflow.keras import layers


def build_model() -> keras.Model:
    return keras.Sequential([
        keras.Input(shape=(28, 28, 1)),
        layers.Conv2D(8, 3, padding="same", activation="relu"),
        layers.MaxPooling2D(2),
        layers.Conv2D(16, 3, padding="same", activation="relu"),
        layers.MaxPooling2D(2),
        layers.Flatten(),
        layers.Dense(64, activation="relu"),
        layers.Dense(10),
    ])

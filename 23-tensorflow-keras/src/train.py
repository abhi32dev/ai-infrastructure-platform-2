"""Trains the Keras CNN on real MNIST via tf.data, using Keras callbacks
(EarlyStopping, ModelCheckpoint) — the idiomatic Keras training loop,
distinct from PyTorch's manual loop in project 19, on purpose: this is
what "TensorFlow fluency" actually means beyond just importing the
package.
"""

from pathlib import Path
import tensorflow as tf
from tensorflow import keras

from model import build_model

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHECKPOINT_PATH = Path(__file__).resolve().parent.parent / "model_checkpoint.keras"

EPOCHS = 5
BATCH_SIZE = 64
TRAIN_SUBSET = 4000
TEST_SUBSET = 1000


def load_data():
    # Newer Keras's mnist.load_data() only accepts a bare filename for
    # `path` (resolved under Keras' own ~/.keras/datasets/ cache), not a
    # full custom path — hit two wrong guesses here (`path=<full path>`
    # raised a ValueError telling me to use `cache_dir`, which doesn't
    # exist either; `inspect.signature` was what actually resolved it).
    # Downloads to Keras' default cache dir instead of this project's
    # own data/ folder as a result.
    (x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
    x_train = x_train[:TRAIN_SUBSET].astype("float32") / 255.0
    y_train = y_train[:TRAIN_SUBSET]
    x_test = x_test[:TEST_SUBSET].astype("float32") / 255.0
    y_test = y_test[:TEST_SUBSET]

    x_train = x_train[..., None]  # add channel dim
    x_test = x_test[..., None]

    train_ds = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(1000).batch(BATCH_SIZE)
    test_ds = tf.data.Dataset.from_tensor_slices((x_test, y_test)).batch(BATCH_SIZE)
    return train_ds, test_ds, (x_test, y_test)


def train():
    train_ds, test_ds, raw_test = load_data()

    model = build_model()
    model.compile(
        optimizer="adam",
        loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )

    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=2, restore_best_weights=True),
        keras.callbacks.ModelCheckpoint(str(CHECKPOINT_PATH), monitor="val_accuracy", save_best_only=True),
    ]

    history = model.fit(train_ds, validation_data=test_ds, epochs=EPOCHS, callbacks=callbacks, verbose=2)

    test_loss, test_acc = model.evaluate(test_ds, verbose=0)
    print(f"\nFinal test accuracy: {test_acc:.4f} | test loss: {test_loss:.4f}")

    return model, history, raw_test


if __name__ == "__main__":
    train()

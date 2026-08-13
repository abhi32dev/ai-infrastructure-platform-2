"""Live tests against the real trained Keras model and real TFLite
export — no mocking. Assumes train.py and export_tflite.py have already
been run once (see README); skips cleanly otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from train import CHECKPOINT_PATH, load_data
from export_tflite import TFLITE_PATH, compare_keras_vs_tflite


@pytest.fixture(scope="module", autouse=True)
def require_trained_model():
    if not CHECKPOINT_PATH.exists() or not TFLITE_PATH.exists():
        pytest.skip("run train.py then export_tflite.py first — see README")


def test_tflite_model_is_smaller_than_keras_checkpoint():
    keras_size = CHECKPOINT_PATH.stat().st_size
    tflite_size = TFLITE_PATH.stat().st_size
    assert tflite_size < keras_size


def test_tflite_predictions_agree_with_keras_on_real_data():
    """The core claim of this project's export step: TFLite conversion
    must preserve model behavior, not just succeed as a file-format
    conversion — proven by direct prediction comparison, not assumed."""
    from tensorflow import keras
    model = keras.models.load_model(CHECKPOINT_PATH)
    _, _, (x_test, y_test) = load_data()

    stats = compare_keras_vs_tflite(model, x_test, n_samples=20)
    assert stats["prediction_agreement"] >= 0.95  # allow rare floating-point edge disagreement


def test_trained_model_beats_random_guessing_baseline():
    """Sanity/regression guard: the trained model must substantially
    beat the 10% random-guess baseline for 10-class MNIST — catches a
    training pipeline that silently produces a useless model."""
    from tensorflow import keras
    model = keras.models.load_model(CHECKPOINT_PATH)
    _, _, (x_test, y_test) = load_data()

    predictions = model.predict(x_test[:200], verbose=0).argmax(axis=1)
    accuracy = (predictions == y_test[:200]).mean()
    assert accuracy > 0.5  # well above the 10% random baseline

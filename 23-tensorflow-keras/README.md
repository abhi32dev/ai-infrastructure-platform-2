# 23 — TensorFlow / Keras

A Keras CNN — deliberately mirroring project 19's PyTorch CNN
architecture on the same real MNIST task, for a direct controlled
framework comparison — trained with idiomatic Keras tooling (`tf.data`,
`EarlyStopping`/`ModelCheckpoint` callbacks), then exported to **TFLite**:
TensorFlow's actual production differentiator over PyTorch, not
demonstrated by project 19's ONNX story.

## Maps to the request
- Direct answer to "have we covered PyTorch, TensorFlow, Keras" — PyTorch
  was covered (projects 10/15/18), TensorFlow/Keras was not. Confirmed by
  the market research: TensorFlow still appears in ~33% of postings
  (PyTorch 37.7%) and remains dominant for edge/enterprise/mobile
  deployment specifically — which is why this project's differentiator is
  TFLite export, not just "the same CNN in a different framework"

## Setup (isolated venv)

```bash
cd 23-tensorflow-keras
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
source .venv/bin/activate
cd src
python train.py           # Keras CNN on real MNIST, tf.data + callbacks
python export_tflite.py   # TFLite export, verified against the original Keras model
```

## Two real API-compatibility snags hit and fixed

**1. `keras.datasets.mnist.load_data()`'s path argument changed twice
across versions I tried.** First attempt (`path=<full path>`) raised
`ValueError: Paths are no longer accepted as the fname argument... use
cache_dir`. Second attempt (`cache_dir=...`) raised `TypeError:
unexpected keyword argument 'cache_dir'` — the error message's own
suggested fix didn't match the installed version's actual signature.
Resolved by inspecting the real signature directly
(`inspect.signature(mnist.load_data)` → `(path='mnist.npz')`, a bare
filename resolved under Keras' own cache dir, not a custom full path) —
documented in `train.py` at the exact line, including both wrong guesses
before the fix, not just the final answer.

**2. `tf.lite.Interpreter` is deprecated** (scheduled for removal in TF
2.20, migrating to the `ai_edge_litert` package) — surfaced as a real
`UserWarning` during testing, not silently ignored. Not migrated in this
project (kept on `tf.lite.Interpreter` since it's still functional and
the current stable API at time of writing), but flagged explicitly as
the next required change when this dependency is upgraded past 2.20.

## Measured results (this run)

```
Epoch 1/5  accuracy: 0.6618  val_accuracy: 0.8250
Epoch 5/5  accuracy: 0.9507  val_accuracy: 0.9250
Final test accuracy: 0.9250

Keras model size:  663,198 bytes
TFLite model size: 212,728 bytes
Size reduction: 67.9%
Keras vs TFLite prediction agreement on 20 samples: 100.0%
```

92.5% test accuracy on real MNIST after 5 epochs (comparable in spirit
to project 19's PyTorch result — different framework, different random
initialization, not expected to match exactly). TFLite conversion: a
**67.9% size reduction** with **100% prediction agreement** against the
original Keras model on held-out samples — proving the mobile/edge
export preserves model behavior, not just that the file conversion
succeeded without error.

## Tests

```bash
cd 23-tensorflow-keras && source .venv/bin/activate && pytest -q
```
3 live tests (run `train.py` then `export_tflite.py` first — tests skip
cleanly otherwise): TFLite is smaller than the Keras checkpoint, TFLite
predictions agree with Keras predictions on real held-out data (the core
export-correctness claim, not just file-size), and the trained model
substantially beats the 10% random-guessing baseline for 10-class MNIST
(a regression guard against a silently-broken training pipeline).

## What to say in an interview

- **Why mirror project 19's exact CNN architecture instead of building
  something TF-specific?** To isolate "which framework" as close to the
  only variable as possible — the interesting comparison is PyTorch's
  manual training loop + ONNX/CPU-quantization story (project 19) versus
  Keras' callback-driven `.fit()` + TFLite mobile-export story (this
  project), on the same task, not two different tasks that happen to use
  different frameworks.
- **Why is TFLite the differentiator, not just "TensorFlow works too"?**
  Because PyTorch can also export to ONNX and run on mobile via ONNX
  Runtime Mobile — the frameworks aren't actually differentiated by "can
  it run on a phone." TFLite's ecosystem maturity (broader hardware
  delegate support — GPU, NNAPI, Core ML, Hexagon DSP — and tighter
  integration with Android/edge tooling) is the real, still-current
  reason TensorFlow remains the default choice for many production mobile
  deployments, which is what the research's "dominant for edge/mobile"
  finding actually points at.
- **Why verify prediction agreement instead of just trusting the
  conversion succeeded?** Same "prove it, don't claim it" discipline as
  project 19's ONNX correctness test — a format conversion can succeed
  (no exception) while subtly changing numerical behavior (different
  op implementations, precision handling). Directly comparing predictions
  on real data is the only way to know the exported model actually still
  does the same thing.
- **Known limitation to volunteer:** this trains on a 4,000-image MNIST
  subset for 5 epochs on CPU — enough to prove the pipeline (data
  loading, `tf.data`, callbacks, TFLite export, correctness verification)
  works end to end, not a claim of a competitively-trained MNIST model
  (which would use the full 60,000-image training set and typically
  exceed 99% accuracy).

# Production Readiness — TensorFlow / Keras

## Current state
Keras CNN mirroring project 19's PyTorch architecture on real MNIST,
trained via idiomatic `tf.data` + callbacks. Exported to TFLite with
100% prediction agreement against the original Keras model. Found and
fixed two real Keras API-compatibility snags (both documented with the
wrong guesses tried first). 3 tests including a random-baseline
regression guard.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Mirrors project 19's exact CNN architecture | Isolates "which framework" as close to the only variable as possible | Doesn't showcase TF/Keras-specific architectural patterns (e.g., `tf.keras.applications` transfer learning) beyond the basics |
| TFLite export as the differentiator, not ONNX again | TFLite is TensorFlow's actual production strength (edge/mobile); re-doing ONNX would be redundant with project 19 | Doesn't demonstrate TF Serving (server-side TF deployment), the other major TF production path |
| Small subset (4,000 images), 5 epochs | Fast, complete local training run | 92.5% accuracy proves the pipeline works, not a competitively-trained MNIST model (full-dataset training typically exceeds 99%) |

## What's missing for real production use
- **TF Serving deployment path** — this project only demonstrates
  TFLite (edge/mobile); a production server-side TensorFlow deployment
  typically uses TF Serving, not shown here
- **Full-dataset training with proper validation** — 4,000/1,000 image
  subset is a demo-scale run; production training needs the full
  dataset, proper train/val/test splits, and hyperparameter tuning
- **Quantization-aware training** — this exports a post-training model to
  TFLite without INT8 quantization applied to the TFLite artifact itself;
  a production mobile deployment would typically also quantize the
  TFLite model (project 19's ONNX quantization findings would likely
  transfer conceptually)
- **Cross-platform TFLite validation** — prediction agreement is verified
  on the same machine that trained the model; a real mobile deployment
  needs validation on actual target devices (different CPU
  architectures, potential numerical differences)

## Scaling considerations
- Training scales the same way any Keras/TF training does — this small
  demo doesn't exercise TF's distributed training strategies
  (`tf.distribute.MirroredStrategy` etc.), which would be the TF-specific
  equivalent of project 15's PyTorch DDP demonstration
- TFLite models are designed for single-device inference (edge/mobile) —
  not a scaling concern in the server sense, but the target constraint is
  model size/latency on constrained hardware, which this project does
  measure (67.9% size reduction)

## Security & compliance considerations
- Not directly applicable to this project's scope — no user data
  handling; a production mobile deployment would need to consider
  on-device model security (model extraction/tampering) which isn't
  addressed here

## Operational readiness
- No automated retraining/re-export pipeline — a production mobile ML
  deployment needs a CI/CD path from model training through TFLite export
  through app-store/OTA model distribution, none of which is built here
- The `tf.lite.Interpreter` deprecation warning (documented) is a real
  operational signal: this project's TFLite verification code will need
  updating to `ai_edge_litert` before TF 2.20

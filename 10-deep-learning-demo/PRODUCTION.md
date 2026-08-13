# Production Readiness — Detection & Tracking

## Current state
Fine-tuned Faster R-CNN (transfer learning) on real PennFudan pedestrian
data, mean IoU 0.875 on held-out set. IoU-based multi-object tracker with
false-positive isolation. Found and fixed a real MPS NaN-loss bug
(forced CPU training). 11 tests covering tracker positive/negative/
regression cases.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| Transfer learning from COCO weights | 144 training images isn't enough to learn features from scratch | Model inherits COCO's biases; not validated on genuinely novel object categories far from COCO's distribution |
| CPU training (MPS forced off) | MPS produced NaN losses — a real, reproduced hardware/framework bug | ~13 minutes training time vs. what would be much faster on a working GPU path |
| Mean IoU instead of full COCO mAP | Simpler, sufficient to prove localization works on one class | Doesn't measure precision/recall tradeoffs across confidence thresholds the way mAP does — not a benchmark-comparable number |
| Greedy IoU matching, no Kalman filter | Demonstrates identity-assignment mechanics clearly and testably | No motion prediction — would lose track through genuine occlusion longer than `MAX_MISSED_FRAMES` |

## What's missing for real production use
- **mAP evaluation** — the standard object-detection benchmark metric
  isn't computed here; a production model needs full precision-recall
  curves across IoU thresholds and confidence levels
- **Multi-class detection** — fine-tuned for one class (pedestrian);
  production detection systems typically need many classes
  simultaneously
- **Kalman-filter or learned tracker** — the greedy IoU tracker has no
  motion model; a production tracking system (DeepSORT, ByteTrack) adds
  motion prediction and appearance embeddings for robustness through
  longer occlusions
- **Batch/streaming inference pipeline** — this project runs inference
  image-by-image; a production video pipeline needs a real-time frame
  ingestion and inference queue

## Scaling considerations
- 144 training images / 3 epochs is a demo-scale training run; a
  production detector needs orders of magnitude more labeled data and
  proper train/val/test splits with augmentation
- CPU inference (proven necessary here due to the MPS bug) is far too
  slow for real-time video (multiple FPS needed); production deployment
  needs a working GPU inference path — the MPS bug specifically should be
  revisited against newer PyTorch/torchvision releases before assuming
  it's permanent

## Security & compliance considerations
- Pedestrian detection raises real privacy considerations if deployed
  against real camera feeds — this demo uses a public academic dataset
  with no such deployment; a production system needs data-handling
  policies for any captured imagery (retention, anonymization, consent)

## Operational readiness
- No model monitoring for detection-quality drift over time (e.g.,
  camera angle changes, lighting shifts degrading real-world accuracy
  silently)
- No confidence-threshold tuning exposed as an operational knob — 
  `SCORE_THRESHOLD` is a code constant, not a runtime-configurable
  parameter an operator could adjust based on false-positive/negative
  tradeoffs observed in production

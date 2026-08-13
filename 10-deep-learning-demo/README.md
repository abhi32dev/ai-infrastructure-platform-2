# 10 — Deep Learning: Object Detection & Tracking

Two independent pieces, matching the resume's coursework claim precisely:
**detection** (fine-tuned Faster R-CNN on real pedestrian images) and
**tracking** (an IoU-based multi-object tracker assigning persistent
identity across frames).

## Maps to resume claims
- "Applied Deep Learning, Object Detection & Tracking (Coursework): Built
  and trained TensorFlow-based object detection and tracking models..."
  (built here in PyTorch — same discipline, different framework)
- IEEE-publication lifecycle language (research → design → train →
  evaluate → deploy), applied to a fine-tuning task

## Part 1: Object Detection

Fine-tunes a COCO-pretrained Faster R-CNN (transfer learning: backbone
features reused, only the box-predictor head retrained) on the
[PennFudan pedestrian dataset](https://www.cis.upenn.edu/~jshi/ped_html/) —
170 images, the same dataset used in torchvision's own official
detection fine-tuning tutorial, independently re-implemented here.

### Setup (isolated venv)

```bash
cd 10-deep-learning-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd data
curl -sL -o PennFudanPed.zip https://www.cis.upenn.edu/~jshi/ped_html/PennFudanPed.zip
unzip -q PennFudanPed.zip
```

### Run it

```bash
source .venv/bin/activate
cd src
python train.py        # fine-tunes, evaluates, saves checkpoint (~13 min on CPU)
python visualize.py    # draws predicted (red) vs ground-truth (green) boxes on sample images
```

### A real bug I hit and how I found it: MPS gives NaN losses

This Mac has Apple Silicon (MPS backend available), so training was tried
there first — losses went to `NaN` by the end of epoch 1. Rather than
guessing, I isolated it: a single forward pass on CPU with the identical
model/data produced finite losses
(`loss_classifier=0.55, loss_box_reg=0.24, ...`), proving the data and
model construction were correct and the divergence was MPS-specific
(a known class of issue with torchvision's RPN/RoIAlign ops on Apple's
MPS backend as of torch 2.13/torchvision 0.28). Fix: force CPU for this
model (documented in `config.py`), trading speed for correctness rather
than silently training on garbage losses.

### Measured results (this run)

| Epoch | Train avg loss | Time |
|---|---|---|
| 1/3 | 0.2536 | 259.6s |
| 2/3 | 0.1250 | 253.9s |
| 3/3 | 0.1007 | 272.0s |

**Held-out mean IoU (best-matched predicted box per ground-truth box,
26 held-out images): 0.8750**

Sample predictions saved to `outputs/prediction_0.png` through
`prediction_3.png` — red boxes are the model's predictions, green boxes
are ground truth. On the images checked, predicted and ground-truth boxes
overlap tightly on both pedestrians in-frame.

## Part 2: Object Tracking

A minimal IoU-based multi-object tracker (SORT-style, no Kalman filter):
each frame's detections are greedily matched to existing tracks by
maximum IoU; unmatched detections start new tracks; tracks unmatched for
`MAX_MISSED_FRAMES` consecutive frames are dropped.

### Run it

```bash
source .venv/bin/activate
cd src
python tracking_demo.py
```

Synthetic 8-frame sequence: one object present every frame, a second
object present only frames 2-6, and a spurious one-frame false detection
injected at frame 4.

### Measured result

| Track | Frames in history |
|---|---|
| Object A (present all 8 frames) | **8** |
| Object B (present frames 2-6) | **5** |
| Spurious false detection (frame 4 only) | **1** |

The spurious detection gets its own track ID (a tracker can't know a
detection is spurious at creation time) but its history length of 1 is
exactly the signal a real system would filter on — a track that's never
re-confirmed by a subsequent detection is very likely a false positive,
distinct from a real object that's merely occluded for a few frames
(which `MAX_MISSED_FRAMES` tolerates).

## Tests

```bash
cd 10-deep-learning-demo && source .venv/bin/activate && pytest -q
```
11 tests, in three categories:
- **Positive path (6):** dataset loads expected image count, dataset items have matching boxes/labels, model builds with correct output classes; tracker: persistent ID across frames, new-object ID assignment, non-overlapping detections don't false-match
- **Negative / edge cases (4):** track pruning after max missed frames, spurious one-frame detection stays isolated (history length 1), an empty first frame doesn't crash the tracker, two detections both overlapping one track never both claim it (greedy-matching regression guard)
- **Regression guard (1):** a briefly-occluded object (missing for fewer than `max_missed` frames) is re-matched to its EXISTING track ID on reappearance, not assigned a new one — the actual point of tolerating missed frames at all

The full training run (~13 min) is exercised via `train.py` directly, not
inside pytest, since a full fine-tuning pass is too slow for a test suite.

## What to say in an interview

- **Why transfer learning instead of training from scratch?** 144 training
  images is nowhere near enough to learn useful convolutional features
  from random initialization — COCO pretraining already learned general
  object-part features (edges, textures, shapes) from millions of images;
  fine-tuning only needs to teach the model the specific box-predictor
  head for one new class, which 144 images is enough data for. This
  mirrors the resume's academic-lifecycle bullet ("research, design,
  implement, TRAIN, evaluate, deploy") — training here specifically means
  fine-tuning, and knowing when full-from-scratch training would actually
  be necessary versus wasteful is the judgment call.
- **The MPS NaN debugging story is the strongest interview material in
  this project** — it's a real, reproducible framework/hardware
  compatibility bug, isolated methodically (single-sample CPU forward
  pass to rule out data/model bugs before suspecting the backend), fixed
  with a documented, deliberate tradeoff (correctness over Apple Silicon
  GPU speed) rather than silently working around it.
- **Why mean-IoU instead of full COCO mAP?** mAP requires computing
  precision-recall curves across multiple IoU thresholds and object
  classes — correct for a benchmark paper, overkill for proving a
  fine-tuned model localizes its one object class in a portfolio project.
  Mean IoU is simpler, directly interpretable ("on average, predicted and
  actual boxes overlap 87.5%"), and sufficient to demonstrate the model
  learned something real rather than memorizing the training set (proven
  by measuring it on the held-out 26 images, never seen during training).
- **Why the tracker doesn't use a Kalman filter:** a Kalman filter adds
  motion prediction (estimate where an occluded object *should* be next
  frame) — valuable for real video with genuine occlusion, but this
  project's point is demonstrating the identity-assignment mechanism
  (IoU matching, track lifecycle, false-positive isolation) clearly and
  testably. Volunteering "I'd add a Kalman filter or a Hungarian-algorithm
  matcher instead of greedy IoU matching for a production video pipeline"
  shows awareness of the gap without over-building a portfolio demo.

"""Evaluation metric: for each ground-truth box, find the best-IoU
predicted box (above a confidence threshold) and average that best IoU
across all ground-truth boxes in the held-out set. Simpler than full
COCO mAP, but directly interpretable and enough to show the fine-tuned
model is actually localizing pedestrians, not just memorizing training
images.
"""

import torch
from torchvision.ops import box_iou

from config import DEVICE

SCORE_THRESHOLD = 0.5


def evaluate_mean_iou(model, eval_dataset, score_threshold: float = SCORE_THRESHOLD):
    model.eval()
    ious = []
    per_image = []

    with torch.no_grad():
        for img, target in eval_dataset:
            img_device = img.to(DEVICE)
            prediction = model([img_device])[0]

            keep = prediction["scores"] >= score_threshold
            pred_boxes = prediction["boxes"][keep].cpu()
            gt_boxes = target["boxes"]

            if len(pred_boxes) == 0 or len(gt_boxes) == 0:
                per_image.append(0.0)
                continue

            iou_matrix = box_iou(gt_boxes, pred_boxes)  # [n_gt, n_pred]
            best_per_gt = iou_matrix.max(dim=1).values
            ious.extend(best_per_gt.tolist())
            per_image.append(float(best_per_gt.mean()))

    mean_iou = sum(ious) / len(ious) if ious else 0.0
    return mean_iou, per_image

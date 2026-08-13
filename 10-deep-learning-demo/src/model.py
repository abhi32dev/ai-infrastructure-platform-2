"""Fine-tunes a COCO-pretrained Faster R-CNN by replacing its box-predictor
head with a fresh one sized for this dataset's classes (background +
pedestrian) — transfer learning, not training from random weights: the
backbone's learned features (edges, textures, object parts) are reused,
only the final classification/regression head is retrained. This is the
standard, correct way to get a usable detector from ~150 training images
instead of the millions COCO provides.
"""

import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from config import NUM_CLASSES


def build_model(num_classes: int = NUM_CLASSES):
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights="DEFAULT")
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    return model

"""Fast tests that don't require a trained checkpoint: dataset loading
correctness and model construction. The slower live training/evaluation
run is exercised via train.py directly (see README), not re-run inside
pytest, since a full fine-tuning pass takes several minutes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dataset import PennFudanDataset
from transforms import get_transform
from model import build_model


def test_dataset_loads_expected_image_count():
    ds = PennFudanDataset(transforms=get_transform(train=False))
    assert len(ds) == 170


def test_dataset_item_has_matching_boxes_and_labels():
    ds = PennFudanDataset(transforms=get_transform(train=False))
    img, target = ds[0]
    assert img.shape[0] == 3  # RGB tensor
    assert target["boxes"].shape[0] == target["labels"].shape[0]
    assert target["boxes"].shape[0] > 0  # every PennFudan image has at least one pedestrian
    # boxes are [xmin, ymin, xmax, ymax] with xmax > xmin, ymax > ymin
    for box in target["boxes"]:
        assert box[2] > box[0]
        assert box[3] > box[1]


def test_model_builds_with_correct_output_classes():
    model = build_model(num_classes=2)
    assert model.roi_heads.box_predictor.cls_score.out_features == 2

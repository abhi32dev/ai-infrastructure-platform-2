"""PennFudan pedestrian-detection dataset. Each image has an instance
segmentation mask (one integer per pedestrian instance); this converts
each mask into a bounding box (min/max of the instance's mask pixels) —
the standard adaptation of a segmentation dataset for a detection model,
following the same structure as torchvision's own object-detection
fine-tuning tutorial (independently re-implemented here, not copy-pasted,
to match this portfolio's file layout and config).
"""

import numpy as np
import torch
from PIL import Image
from pathlib import Path

from config import DATA_DIR


class PennFudanDataset(torch.utils.data.Dataset):
    def __init__(self, root: Path = DATA_DIR, transforms=None):
        self.root = root
        self.transforms = transforms
        self.imgs = sorted((root / "PNGImages").iterdir())
        self.masks = sorted((root / "PedMasks").iterdir())
        assert len(self.imgs) == len(self.masks)

    def __len__(self):
        return len(self.imgs)

    def __getitem__(self, idx):
        img = Image.open(self.imgs[idx]).convert("RGB")
        mask = Image.open(self.masks[idx])
        mask = np.array(mask)

        obj_ids = np.unique(mask)
        obj_ids = obj_ids[1:]  # first id is background (0)
        masks = mask == obj_ids[:, None, None]

        boxes = []
        for m in masks:
            pos = np.where(m)
            xmin, xmax = pos[1].min(), pos[1].max()
            ymin, ymax = pos[0].min(), pos[0].max()
            boxes.append([xmin, ymin, xmax, ymax])

        boxes = torch.as_tensor(boxes, dtype=torch.float32)
        labels = torch.ones((len(obj_ids),), dtype=torch.int64)  # single class: pedestrian=1
        area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])

        target = {
            "boxes": boxes,
            "labels": labels,
            "image_id": torch.tensor([idx]),
            "area": area,
            "iscrowd": torch.zeros((len(obj_ids),), dtype=torch.int64),
        }

        if self.transforms is not None:
            img, target = self.transforms(img, target)
        return img, target


def collate_fn(batch):
    return tuple(zip(*batch))

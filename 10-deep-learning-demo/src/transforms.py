"""Minimal image+target transform pipeline (PIL image -> tensor, optional
horizontal flip with boxes flipped to match) — deliberately small and
dependency-free rather than pulling in torchvision.transforms.v2's full
detection transform machinery, since only two transforms are needed here.
"""

import random
import torch
import torchvision.transforms.functional as F


class ToTensor:
    def __call__(self, image, target):
        image = F.to_tensor(image)
        return image, target


class RandomHorizontalFlip:
    def __init__(self, p=0.5):
        self.p = p

    def __call__(self, image, target):
        if random.random() < self.p:
            width = image.shape[-1] if torch.is_tensor(image) else image.width
            image = F.hflip(image)
            boxes = target["boxes"]
            boxes[:, [0, 2]] = width - boxes[:, [2, 0]]
            target["boxes"] = boxes
        return image, target


class Compose:
    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, image, target):
        for t in self.transforms:
            image, target = t(image, target)
        return image, target


def get_transform(train: bool):
    transforms = [ToTensor()]
    if train:
        transforms.append(RandomHorizontalFlip(0.5))
    return Compose(transforms)

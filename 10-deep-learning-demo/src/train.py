"""Full lifecycle in one script: load data -> split train/eval -> train ->
evaluate (mean IoU of best-matched predicted box per ground-truth box) ->
checkpoint. Mirrors the resume's IEEE-publication lifecycle language
(research -> design -> implement -> train -> evaluate -> deploy), scoped
to a fine-tuning task instead of a from-scratch architecture.
"""

import time
import torch
from torch.utils.data import DataLoader, Subset

from config import (
    BATCH_SIZE, EPOCHS, LEARNING_RATE, TRAIN_FRACTION, RNG_SEED,
    DEVICE, OUTPUTS_DIR, CHECKPOINT_PATH,
)
from dataset import PennFudanDataset, collate_fn
from transforms import get_transform
from model import build_model
from evaluate import evaluate_mean_iou


def split_dataset():
    full_train = PennFudanDataset(transforms=get_transform(train=True))
    full_eval = PennFudanDataset(transforms=get_transform(train=False))

    n = len(full_train)
    generator = torch.Generator().manual_seed(RNG_SEED)
    indices = torch.randperm(n, generator=generator).tolist()
    split = int(n * TRAIN_FRACTION)

    train_ds = Subset(full_train, indices[:split])
    eval_ds = Subset(full_eval, indices[split:])
    return train_ds, eval_ds


def train():
    print(f"Device: {DEVICE}")
    train_ds, eval_ds = split_dataset()
    print(f"Train images: {len(train_ds)} | Eval images: {len(eval_ds)}")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, collate_fn=collate_fn)

    model = build_model().to(DEVICE)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=LEARNING_RATE, momentum=0.9, weight_decay=0.0005)

    model.train()
    for epoch in range(1, EPOCHS + 1):
        epoch_start = time.time()
        total_loss = 0.0
        for images, targets in train_loader:
            images = [img.to(DEVICE) for img in images]
            targets = [{k: v.to(DEVICE) for k, v in t.items()} for t in targets]

            loss_dict = model(images, targets)
            loss = sum(loss_dict.values())

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        print(f"epoch {epoch}/{EPOCHS}: avg_loss={avg_loss:.4f} ({time.time()-epoch_start:.1f}s)")

    OUTPUTS_DIR.mkdir(exist_ok=True)
    torch.save(model.state_dict(), CHECKPOINT_PATH)
    print(f"\nCheckpoint saved to {CHECKPOINT_PATH}")

    print("\nEvaluating on held-out set...")
    mean_iou, per_image = evaluate_mean_iou(model, eval_ds)
    print(f"Mean IoU (best-matched box per ground truth) on {len(eval_ds)} held-out images: {mean_iou:.4f}")
    return model, mean_iou


if __name__ == "__main__":
    train()

"""Loads the fine-tuned checkpoint, runs inference on a few held-out
images, and saves them with predicted boxes drawn on — the visual proof
the model localizes pedestrians, to look at directly rather than trust a
single aggregate metric.
"""

from PIL import ImageDraw
import torch
import torchvision.transforms.functional as F

from config import DEVICE, CHECKPOINT_PATH, OUTPUTS_DIR
from dataset import PennFudanDataset
from transforms import get_transform
from model import build_model
from evaluate import SCORE_THRESHOLD


def visualize_predictions(n_images: int = 4):
    model = build_model().to(DEVICE)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=DEVICE))
    model.eval()

    dataset = PennFudanDataset(transforms=get_transform(train=False))
    OUTPUTS_DIR.mkdir(exist_ok=True)

    with torch.no_grad():
        for idx in range(min(n_images, len(dataset))):
            img_tensor, target = dataset[idx]
            prediction = model([img_tensor.to(DEVICE)])[0]

            pil_img = F.to_pil_image(img_tensor)
            draw = ImageDraw.Draw(pil_img)

            for box, score in zip(prediction["boxes"], prediction["scores"]):
                if score < SCORE_THRESHOLD:
                    continue
                box = box.tolist()
                draw.rectangle(box, outline="red", width=3)
                draw.text((box[0], max(0, box[1] - 12)), f"{score:.2f}", fill="red")

            for gt_box in target["boxes"].tolist():
                draw.rectangle(gt_box, outline="lime", width=1)

            out_path = OUTPUTS_DIR / f"prediction_{idx}.png"
            pil_img.save(out_path)
            print(f"Saved {out_path} (red=predicted, green=ground truth)")


if __name__ == "__main__":
    visualize_predictions()

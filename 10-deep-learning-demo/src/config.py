from pathlib import Path
import torch

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "PennFudanPed"
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
CHECKPOINT_PATH = OUTPUTS_DIR / "fasterrcnn_pennfudan.pt"

NUM_CLASSES = 2  # background + pedestrian
BATCH_SIZE = 2
EPOCHS = 3
LEARNING_RATE = 0.005
TRAIN_FRACTION = 0.85  # rest held out for evaluation
RNG_SEED = 42

# NOTE: torchvision's Faster R-CNN (RPN/RoIAlign ops) produces NaN losses
# on Apple's MPS backend as of torch 2.13/torchvision 0.28 (reproduced:
# CPU forward pass on one sample gives finite losses, MPS training runs to
# NaN by end of epoch 1). CUDA is unaffected by this; MPS is excluded here
# until upstream fixes it. Falling back to CPU trades speed for correctness.
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

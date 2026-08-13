from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "ml-100k"
TRAIN_FILE = DATA_DIR / "ua.base"   # official MovieLens 80/20 split
TEST_FILE = DATA_DIR / "ua.test"
ITEM_FILE = DATA_DIR / "u.item"

N_USERS = 943
N_ITEMS = 1682

LATENT_FACTORS = 20
LEARNING_RATE = 0.01
REGULARIZATION = 0.02
EPOCHS = 20
RNG_SEED = 42

TOP_K = 10  # for precision@k / recall@k
RELEVANCE_THRESHOLD = 4  # a rating >= 4 (out of 5) counts as "relevant" for precision/recall

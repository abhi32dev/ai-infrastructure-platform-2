WORLD_SIZE = 4          # number of local processes simulating "GPUs"
BACKEND = "gloo"         # CPU-compatible collective backend; swap to "nccl" for real multi-GPU —
                         # the training code below does not otherwise change
EPOCHS = 5
BATCH_SIZE_PER_RANK = 32
LR = 0.05
N_SAMPLES = 4000          # total synthetic dataset size, sharded across ranks
N_FEATURES = 20
RNG_SEED = 42

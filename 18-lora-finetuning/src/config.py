BASE_MODEL = "distilgpt2"  # small (82M params), fast on CPU, produces real coherent English

# LoRA hyperparameters
LORA_R = 8
LORA_ALPHA = 16
LORA_DROPOUT = 0.05
TARGET_MODULES = ["c_attn"]  # GPT-2-family attention projection — where LoRA adapts the most useful signal

EPOCHS = 8
LR = 2e-4
BATCH_SIZE = 2
MAX_LENGTH = 96

OUTPUT_DIR = "adapter_checkpoint"

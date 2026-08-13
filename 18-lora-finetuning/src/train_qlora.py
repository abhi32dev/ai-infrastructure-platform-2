"""Real QLoRA fine-tuning: the base model loads in 4-bit (via
bitsandbytes' BitsAndBytesConfig — genuinely quantized Linear4bit layers,
verified directly, not assumed), then LoRA adapter matrices (via Hugging
Face `peft`) are trained on top while the quantized base weights stay
frozen. Prints the exact trainable-parameter percentage, the actual
number PEFT/QLoRA exists to shrink.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

from config import (
    BASE_MODEL, LORA_R, LORA_ALPHA, LORA_DROPOUT, TARGET_MODULES,
    EPOCHS, LR, BATCH_SIZE, MAX_LENGTH, OUTPUT_DIR,
)
from dataset import build_training_texts


def load_quantized_base():
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float32)
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, quantization_config=bnb_config)
    return model


def count_quantized_linear_layers(model) -> int:
    return sum(1 for _, m in model.named_modules() if type(m).__name__ == "Linear4bit")


def build_lora_model(base_model):
    base_model = prepare_model_for_kbit_training(base_model)
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        task_type="CAUSAL_LM",
    )
    return get_peft_model(base_model, lora_config)


def trainable_param_stats(model) -> dict:
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return {"trainable": trainable, "total": total, "pct": 100 * trainable / total}


def train():
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token

    base_model = load_quantized_base()
    n_quantized = count_quantized_linear_layers(base_model)
    print(f"Verified {n_quantized} real Linear4bit (quantized) layers in the base model.")

    model = build_lora_model(base_model)
    stats = trainable_param_stats(model)
    print(f"Trainable params: {stats['trainable']:,} / {stats['total']:,} "
          f"({stats['pct']:.3f}% — this is the parameter-efficiency QLoRA exists to deliver)")

    texts = build_training_texts()
    encodings = tokenizer(texts, truncation=True, max_length=MAX_LENGTH, padding="max_length", return_tensors="pt")
    input_ids = encodings["input_ids"]
    attention_mask = encodings["attention_mask"]
    labels = input_ids.clone()
    labels[attention_mask == 0] = -100  # ignore padding in the loss

    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR)
    model.train()

    n_examples = input_ids.shape[0]
    for epoch in range(1, EPOCHS + 1):
        total_loss = 0.0
        n_batches = 0
        for start in range(0, n_examples, BATCH_SIZE):
            batch_ids = input_ids[start:start + BATCH_SIZE]
            batch_mask = attention_mask[start:start + BATCH_SIZE]
            batch_labels = labels[start:start + BATCH_SIZE]

            optimizer.zero_grad()
            outputs = model(input_ids=batch_ids, attention_mask=batch_mask, labels=batch_labels)
            outputs.loss.backward()
            optimizer.step()

            total_loss += outputs.loss.item()
            n_batches += 1

        print(f"epoch {epoch}/{EPOCHS}: avg_loss={total_loss / n_batches:.4f}")

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"\nAdapter saved to {OUTPUT_DIR} (LoRA weights only — a few MB, not a full model copy)")
    return model, tokenizer, stats


if __name__ == "__main__":
    train()

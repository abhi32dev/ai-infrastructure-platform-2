"""Generates answers to held-out questions (worded differently from the
training examples) using the base model alone vs. the base model + LoRA
adapter, to show the fine-tuning actually changed generation behavior
toward the Aegis-platform Q&A style, not just memorized training loss.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

from config import BASE_MODEL, OUTPUT_DIR
from dataset import held_out_questions


def generate(model, tokenizer, question: str, max_new_tokens: int = 40) -> str:
    prompt = f"Q: {question}\nA:"
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    full_text = tokenizer.decode(output[0], skip_special_tokens=True)
    return full_text[len(prompt):].split("Q:")[0].strip()


def compare():
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float32)
    base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, quantization_config=bnb_config)

    fine_tuned = PeftModel.from_pretrained(base_model, OUTPUT_DIR)

    print("Loading a SECOND fresh copy of the base model for a fair before/after comparison...")
    base_only = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float32)
    )

    results = []
    for question in held_out_questions():
        before = generate(base_only, tokenizer, question)
        after = generate(fine_tuned, tokenizer, question)
        results.append({"question": question, "before": before, "after": after})
        print(f"\nQ: {question}")
        print(f"  BEFORE (base model):        {before[:120]!r}")
        print(f"  AFTER  (base model + LoRA): {after[:120]!r}")

    return results


if __name__ == "__main__":
    compare()

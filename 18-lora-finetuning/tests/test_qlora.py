"""Live tests against the real quantized model + PEFT stack — no
mocking, since the entire point is proving 4-bit quantization and LoRA
adapter training actually happened.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from train_qlora import load_quantized_base, count_quantized_linear_layers, build_lora_model, trainable_param_stats


def test_base_model_loads_with_real_quantized_layers():
    """Regression guard on the core finding this project's setup phase
    depends on: bitsandbytes must produce real Linear4bit layers on this
    hardware, not silently fall back to full precision."""
    model = load_quantized_base()
    n_quantized = count_quantized_linear_layers(model)
    assert n_quantized > 0


def test_lora_reduces_trainable_params_to_a_small_fraction():
    """The actual parameter-efficiency claim, measured directly: LoRA's
    trainable fraction must be small (< 5%) — if this regressed to
    ~100%, LoRA freezing wasn't applied and the 'parameter-efficient'
    claim would be false."""
    base_model = load_quantized_base()
    model = build_lora_model(base_model)
    stats = trainable_param_stats(model)
    assert stats["pct"] < 5.0
    assert stats["trainable"] > 0  # not zero — something is actually trainable


def test_lora_adapter_only_adds_target_module_parameters():
    """Negative case: parameters OUTSIDE the configured target_modules
    (c_attn) must remain frozen — proves LoRA scoped correctly rather
    than accidentally unfreezing the whole model."""
    base_model = load_quantized_base()
    model = build_lora_model(base_model)
    for name, param in model.named_parameters():
        if param.requires_grad:
            assert "lora" in name.lower(), f"unexpected trainable param outside LoRA adapter: {name}"

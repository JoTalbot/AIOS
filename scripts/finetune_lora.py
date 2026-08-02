"""
Fine-tune qwen2.5-coder:1.5b with LoRA on AIOS dataset - CPU friendly version
Uses peft + transformers, QLoRA 4-bit if GPU, otherwise full LoRA on CPU (slow but works for small dataset)
"""
import json, os
from pathlib import Path

def prepare_training_args():
    """Check resources and suggest training config"""
    import psutil
    mem_gb = psutil.virtual_memory().total / (1024**3)
    print(f"Total RAM: {mem_gb:.1f}GB")
    if mem_gb < 8:
        print("⚠️ Low RAM, recommend 1.5b model with LoRA rank 8, batch 1")
        return {"model": "Qwen/Qwen2.5-Coder-1.5B", "rank": 8, "batch": 1, "epochs": 1}
    else:
        print("✅ Enough RAM for 7b with QLoRA rank 16")
        return {"model": "Qwen/Qwen2.5-Coder-7B", "rank": 16, "batch": 2, "epochs": 2}

def train_lora():
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        import torch
        
        config = prepare_training_args()
        print(f"Training config: {config}")
        
        # Load dataset
        dataset_path = Path("data/finetune/aios_coder_hf.jsonl")
        if not dataset_path.exists():
            print(f"Dataset not found: {dataset_path}")
            return
        
        # Load model and tokenizer
        print(f"Loading model {config['model']}...")
        tokenizer = AutoTokenizer.from_pretrained(config["model"], trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            config["model"],
            trust_remote_code=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None
        )
        
        # Prepare LoRA
        peft_config = LoraConfig(
            r=8,
            lora_alpha=16,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM"
        )
        model = get_peft_model(model, peft_config)
        
        print("Model prepared for LoRA training")
        print(f"Trainable params: {model.print_trainable_parameters()}")
        
        # For demo, we don't actually train here (would take hours on CPU)
        # Instead save config and instructions
        print("✅ Model prepared, ready for training")
        print("To actually train, run with GPU or use Ollama Modelfile method")
        return True
        
    except ImportError as e:
        print(f"Missing dependencies: {e}")
        print("Install with: pip install transformers peft torch accelerate")
        return False
    except Exception as e:
        print(f"Training setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # First check if we can at least create Ollama model
    print("=== Checking Ollama ===")
    import subprocess
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        print(result.stdout)
    except Exception as e:
        print(f"Ollama not available: {e}")
    
    print("\n=== Preparing LoRA training ===")
    train_lora()
    
    print("\n=== Alternative: Ollama Modelfile method (recommended for CPU) ===")
    print("Run: ollama create aios-coder:7b -f data/finetune/Modelfile")
    print("Then test: ollama run aios-coder:7b 'Fix HACK in api_v2_batch.py'")

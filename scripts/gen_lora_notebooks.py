#!/usr/bin/env python3
"""
AIOS - Генератор ноутбуков LoRA Fine-Tuning (Этап 3)

Создаёт:
  docs/AIOS_Colab_LoRA_FineTune.ipynb  - Unsloth LoRA на Qwen2.5-7B / Llama-3.1-8B
  docs/AIOS_Colab_GGUF_Quantize.ipynb  - конвертация модели в GGUF / AWQ

Источник датасета: data/finetune/aios_coder_hf.jsonl (формат OpenAI messages).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/root/AIOS")
DOCS = REPO / "docs"


def md(s: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}


def code(s: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": s.splitlines(keepends=True)}


def base_meta():
    return {"colab": {"provenance": []}, "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"}}


def nb_lora() -> dict:
    cells = [
        md(
            "# 🧠 AIOS LoRA Fine-Tuning (Unsloth / PEFT)\n\n"
            "Обучение собственного LoRA-адаптера на **Qwen2.5-7B-Instruct** (или Llama-3.1-8B) "
            "на базе датасета AIOS.\n\n"
            "**Среда выполнения → T4 GPU** (Unsloth оптимизирован для Colab).\n\n"
            "Датасет: загрузите `aios_coder_hf.jsonl` (с VPS, папка `data/finetune/`) в сессию Colab."
        ),
        code("!pip install -q unsloth\n"
             "import torch\n"
             "from unsloth import FastLanguageModel\n"
             "print('✅ Unsloth установлен, CUDA:', torch.cuda.is_available())"),
        code("# === ЯЧЕЙКА 2: Загрузка датасета ===\n"
             "import json, os\n"
             "with open('aios_coder_hf.jsonl') as f:\n"
             "    dataset = [json.loads(l) for l in f if l.strip()]\n"
             "print('✅ Датасет:', len(dataset), 'примеров')\n"
             "print(dataset[0]['messages'][0]['content'][:80])"),
        code("# === ЯЧЕЙКА 3: Загрузка базовой модели (4bit LoRA) ===\n"
             "from unsloth import FastLanguageModel\n"
             "model, tokenizer = FastLanguageModel.from_pretrained(\n"
             "    model_name='Qwen/Qwen2.5-7B-Instruct',\n"
             "    max_seq_length=2048,\n"
             "    dtype=None,\n"
             "    load_in_4bit=True,\n"
             ")\n"
             "model = FastLanguageModel.get_peft_model(\n"
             "    model,\n"
             "    r=16, lora_alpha=32, lora_dropout=0.05,\n"
             "    target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],\n"
             "    use_gradient_checkpointing=True,\n"
             ")\n"
             "print('✅ Модель + LoRA готовы')"),
        code("# === ЯЧЕЙКА 4: Форматирование + обучение ===\n"
             "from trl import SFTTrainer\n"
             "from transformers import TrainingArguments\n"
             "from datasets import Dataset\n"
             "\n"
             "def fmt(ex):\n"
             "    m = ex['messages']\n"
             "    return {'text': tokenizer.apply_chat_template(m, tokenize=False)}\n"
             "ds = Dataset.from_list(dataset).map(fmt)\n"
             "\n"
             "trainer = SFTTrainer(\n"
             "    model=model, tokenizer=tokenizer, train_dataset=ds,\n"
             "    dataset_text_field='text', max_seq_length=2048,\n"
             "    args=TrainingArguments(\n"
             "        per_device_train_batch_size=2, gradient_accumulation_steps=4,\n"
             "        warmup_steps=5, num_train_epochs=3, learning_rate=2e-4,\n"
             "        fp16=not torch.cuda.is_bf16_supported(),\n"
             "        bf16=torch.cuda.is_bf16_supported(),\n"
             "        logging_steps=1, output_dir='outputs',\n"
             "    ),\n"
             ")\n"
             "trainer.train()\n"
             "print('✅ LoRA обучена')"),
        code("# === ЯЧЕЙКА 5: Сохранение LoRA + слияние ===\n"
             "FastLanguageModel.for_inference(model)\n"
             "model.save_pretrained('lora_model')\n"
             "tokenizer.save_pretrained('lora_model')\n"
             "# Слияние LoRA с базовой моделью для инференса\n"
             "model = model.merge_and_unload()\n"
             "model.save_pretrained('merged_model')\n"
             "tokenizer.save_pretrained('merged_model')\n"
             "print('✅ Сохранено: lora_model/ и merged_model/')\n"
             "print('   Загрузите папку на VPS (или HF Hub) для инференса.')"),
        code("# === ЯЧЕЙКА 6: Проверка генерации ===\n"
             "FastLanguageModel.for_inference(model)\n"
             "msgs = [{'role':'user','content':'Fix a security issue: hard-coded API key in aios_core. Give Python code.'}]\n"
             "inputs = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_tensors='pt').to('cuda')\n"
             "out = model.generate(**inputs, max_new_tokens=120)\n"
             "print(tokenizer.decode(out[0][inputs.shape[1]:], skip_special_tokens=True))"),
    ]
    return {"cells": cells, "metadata": base_meta(), "nbformat": 4, "nbformat_minor": 0}


def nb_gguf() -> dict:
    cells = [
        md(
            "# 🗜️ AIOS GGUF / AWQ Quantization\n\n"
            "Конвертация слитой LoRA-модели (или базовой) в компактный **GGUF** для быстрого "
            "инференса на VPS через llama.cpp / Ollama (порт 11434 уже слушает).\n\n"
            "**T4 GPU / High-RAM**."
        ),
        code("!pip install -q transformers torch\n"
             "import torch, os\n"
             "print('✅ Зависимости установлены')"),
        code("# === ЯЧЕЙКА 2: Загрузка слитой модели ===\n"
             "from transformers import AutoModelForCausalLM, AutoTokenizer\n"
             "model = AutoModelForCausalLM.from_pretrained('merged_model', torch_dtype=torch.float16, device_map='auto')\n"
             "tokenizer = AutoTokenizer.from_pretrained('merged_model')\n"
             "print('✅ Модель загружена')"),
        code("# === ЯЧЕЙКА 3: Экспорт в safetensors для llama.cpp ===\n"
             "!pip install -q huggingface_hub\n"
             "os.makedirs('export_gguf', exist_ok=True)\n"
             "model.save_pretrained('export_gguf')\n"
             "tokenizer.save_pretrained('export_gguf')\n"
             "print('✅ Экспортировано в export_gguf/')\n"
             "print('Дальше в Colab: pip install llama-cpp-python и конвертация через convert_hf_to_gguf.py')"),
        code("# === ЯЧЕЙКА 4: Конвертация в GGUF (llama.cpp) ===\n"
             "!git clone -q --depth 1 https://github.com/ggerganov/llama.cpp\n"
             "!python llama.cpp/convert_hf_to_gguf.py export_gguf --outfile aios_model.gguf --outtype q8_0\n"
             "print('✅ Готово: aios_model.gguf')\n"
             "print('Загрузите aios_model.gguf на VPS и запустите Ollama / llama.cpp.')"),
    ]
    return {"cells": cells, "metadata": base_meta(), "nbformat": 4, "nbformat_minor": 0}


def write(p: Path, nb: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"✅ {p} ({p.stat().st_size} байт)")


if __name__ == "__main__":
    write(DOCS / "AIOS_Colab_LoRA_FineTune.ipynb", nb_lora())
    write(DOCS / "AIOS_Colab_GGUF_Quantize.ipynb", nb_gguf())
    print("Ноутбуки LoRA сгенерированы.")

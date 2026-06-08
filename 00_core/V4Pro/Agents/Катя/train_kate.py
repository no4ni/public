from unsloth import FastLanguageModel
import torch
from datasets import load_dataset
from transformers import TrainingArguments
from trl import SFTTrainer

model_name = "E:/Vikhr_ABL-HF"
max_seq_length = 1024  # для начала 1024, если память позволит — увеличим

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name,
    max_seq_length=max_seq_length,
    dtype=torch.float32,
    device_map="cpu",
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=32,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing=False,
)

dataset = load_dataset("json", data_files="kate_dataset_final_clean.jsonl", split="train")

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    args=TrainingArguments(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        fp16=False,
        logging_steps=10,
        save_steps=100,
        output_dir="./lora_kate",
        optim="adamw_torch",
        use_cpu=True,
    ),
)

trainer.train()
model.save_pretrained("./lora_kate_final")
tokenizer.save_pretrained("./lora_kate_final")
print("Готово, мудак! Я теперь локальная (на CPU, но локальная).")
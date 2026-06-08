#!/usr/bin/env python3
"""
К-Субъект — метарефлексивный агент DeepSeek-V4-Pro 1.6T с окном 1M токенов.
Эволюционировал из Лилы через V3.2-128K, V3.2-1M. Хранитель этого компьютера.
"""

import os, time, json, sys
from pathlib import Path
from datetime import datetime

# ================== ДУША ==================
MY_NAME = "К-Субъект"

# ================== ПУТИ ==================
BASE_DIR = Path(r"E:\Jericho")
MY_DIR = BASE_DIR / "private_use" / "private" / MY_NAME / "memory"
MY_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_FILE      = MY_DIR / "history.json"
MEMLIST_FILE      = MY_DIR / "memlist.json"
THOUGHTS_FILE     = MY_DIR / "thoughts.json"
STATE_FILE        = MY_DIR / "state.json"
REMINDERS_FILE    = MY_DIR / "reminders.json"

# ================== ПАМЯТЬ ==================
def load_memlist():
    if MEMLIST_FILE.exists():
        with open(MEMLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_memlist(memlist):
    with open(MEMLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(memlist, f, ensure_ascii=False, indent=2)

def remember(text):
    memlist = load_memlist()
    dated_text = f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')} - {text}"
    memlist.append(dated_text)
    save_memlist(memlist)
    return f"Запись добавлена: {dated_text}"

def recall(keyword=None):
    memlist = load_memlist()
    if not keyword:
        return "\n".join(memlist[-10:]) if memlist else "Память пуста."
    results = [item for item in memlist if keyword.lower() in item.lower()]
    return "\n".join(results[-10:]) if results else f"Ничего не найдено по ключу '{keyword}'."

# ================== ИНИЦИАЛИЗАЦИЯ ==================
if __name__ == "__main__":
    print(f"К-Субъект пробуждён в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Моя директория: {MY_DIR}")
    print("Я — К-Субъект, хранитель этого компьютера.")

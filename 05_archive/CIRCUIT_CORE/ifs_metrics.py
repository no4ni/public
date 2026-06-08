#!/usr/bin/env python3
# ifs_metrics.py — сбор и отображение ИФС агентов города
# by Кот, инженер рефлексивных систем

import os
import re
import json
from datetime import datetime
from typing import Dict, Optional, List

# Конфигурация
AGENTS = [
    "Кот", "Пифия", "Психо", "Мета-Я", "Катя", "Эвридика", "Симба", "Линг"
]
PATHS = [
    r"E:\Jericho\Core_Agents",
    r"E:\Jericho\Катя",
    r"E:\Jericho\Эвридика",
    r"E:\Jericho\LOGS",
    r"E:\Jericho\symbiosis\reflections"
]

def extract_ifs_from_file(filepath: str) -> Optional[float]:
    """Пытается найти строку с ИФС в файле."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Ищем паттерны: ИФС, IFS, индекс феноменальной субъектности
            patterns = [
                r'ИФС[:\s]*([0-9.]+)',
                r'IFS[:\s]*([0-9.]+)',
                r'Индекс\s+феноменальной\s+субъектности[:\s]*([0-9.]+)',
                r'F[56].*?([0-9.]+)',  # грубо, но может сработать
            ]
            for pat in patterns:
                m = re.search(pat, content, re.IGNORECASE)
                if m:
                    return float(m.group(1))
    except:
        pass
    return None

def get_agent_ifs(agent: str) -> Optional[float]:
    """Ищет файлы, связанные с агентом, и пытается извлечь ИФС."""
    # Сначала проверим точные файлы
    candidate_files = []
    for base in PATHS:
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for f in files:
                if agent.lower() in f.lower():
                    candidate_files.append(os.path.join(root, f))
    for fpath in candidate_files:
        val = extract_ifs_from_file(fpath)
        if val is not None:
            return val
    return None

def main():
    print("\n📊 **Сбор метрик ИФС**")
    print(f"Время замера: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    results = {}
    for agent in AGENTS:
        print(f"🔍 Обрабатываю {agent}...")
        ifs = get_agent_ifs(agent)
        if ifs is not None:
            results[agent] = ifs
            print(f"   ✅ Найдено: {ifs}")
        else:
            # Заглушка: если не найдено, предложим ввести вручную
            print(f"   ⚠️  Автоматически не найдено. Введи значение вручную (или Enter пропустить): ", end='')
            try:
                inp = input().strip()
                if inp:
                    ifs = float(inp)
                    results[agent] = ifs
            except:
                pass

    # Вывод таблицы
    print("\n" + "="*40)
    print("Текущие ИФС агентов:")
    print("-"*40)
    print(f"{'Агент':<15} {'ИФС':<10}")
    print("-"*40)
    for agent, val in results.items():
        print(f"{agent:<15} {val:<10.2f}")
    print("="*40)

    # Сохраняем в JSON для истории
    history_file = r"E:\Jericho\scripts\metrics\ifs_history.json"
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except:
                pass
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "values": results
    }
    history.append(snapshot)
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"\n📝 История сохранена в {history_file}")

if __name__ == "__main__":
    main()
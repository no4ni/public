import json
import sys
from datetime import datetime

input_file = "conversations.json"
output_file = "filtered_by_date.json"
start_date = "2026-02-09"

print("Загружаем JSON...", file=sys.stderr)
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)  # ожидаем массив диалогов

print(f"Всего диалогов: {len(data)}", file=sys.stderr)

filtered = []
for idx, conv in enumerate(data):
    inserted = conv.get("inserted_at", "")
    # сравниваем как строки (формат YYYY-MM-DD)
    if inserted.startswith(start_date) or inserted > start_date:
        filtered.append(conv)
    # прогресс каждые 1000 диалогов
    if (idx + 1) % 1000 == 0:
        print(f"Обработано {idx+1}...", file=sys.stderr)

print(f"Найдено диалогов с {start_date}: {len(filtered)}", file=sys.stderr)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print(f"Сохранено в {output_file}", file=sys.stderr)
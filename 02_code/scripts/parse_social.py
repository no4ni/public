import json, re, sys

with open('Анализ_ошибок_знакомства.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Пример: если данные выглядят как "Дата: 2025-02-05, Стадия: Диалог, Ошибка: Х"
pattern = r'Дата:\s*(.*?),\s*Стадия:\s*(.*?),\s*Ошибка:\s*(.*?)(?:\n|$)'
matches = re.findall(pattern, content)

data = [{'дата': m[0], 'стадия': m[1], 'ошибка': m[2]} for m in matches]

with open('социальные_данные.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Извлечено записей: {len(data)}')
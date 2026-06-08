import re, json, sys

with open('Анализ_ошибок_знакомства.md', 'r', encoding='utf-8') as f:
    text = f.read()

# Ищет блоки между "**Дата:** `YYYY-MM-DD`" и следующим заголовком "##"
entries = []
pattern = r'\*\*Дата:\*\*\s*`(\d{4}-\d{2}-\d{2})`[\s\S]*?\*\*Стадия взаимодействия:\*\*\s*`\[([^]]+)\]`'
matches = re.findall(pattern, text)

for date, stage in matches:
    entries.append({'дата': date, 'стадия': stage})

with open('социальные_данные.json', 'w', encoding='utf-8') as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print(f'Найдено записей: {len(entries)}')
for e in entries:
    print(f"  {e['дата']}: {e['стадия']}")
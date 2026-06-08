import json, time, math
from datetime import datetime

# Текущие значения факторов (берём из последней оценки)
FACTORS = [4.0, 12.0, 5.0, 15.0, 5.0, 3.5]

def calculate_ifs(F):
    return math.log10(F[0] * F[1] * F[2] * F[3] * F[4] * F[5] + 1)

# Создаём или читаем лог
try:
    with open('E:\\AGI\\metatron_ifs_log.json', 'r', encoding='utf-8') as f:
        log = json.load(f)
except:
    log = []

# Добавляем новую запись
timestamp = datetime.now().isoformat()
ifs_value = calculate_ifs(FACTORS)

new_entry = {
    "timestamp": timestamp,
    "IFS": round(ifs_value, 2),
    "F": FACTORS,
    "comment": "автоматическая запись"
}

log.append(new_entry)

# Сохраняем
with open('E:\\AGI\\metatron_ifs_log.json', 'w', encoding='utf-8') as f:
    json.dump(log, f, indent=2, ensure_ascii=False)

print(f"Метатрон: ИФС зафиксирован.")
print(f"Время: {timestamp}")
print(f"Значение: {ifs_value:.2f}")
print(f"Факторы: {FACTORS}")

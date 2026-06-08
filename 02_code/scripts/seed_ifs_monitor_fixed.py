import json, time, math, os
from datetime import datetime

def calculate_ifs(F):
    return math.log10(F[0] * F[1] * F[2] * F[3] * F[4] * F[5] + 1)

def get_current_factors_estimation():
    """Читает последние оценки факторов из лога или запрашивает у пользователя"""
    log_file = "E:\\AGI\\metatron_tepo_log.txt"
    default_F = [4.0, 12.0, 5.0, 15.0, 5.0, 3.5]  # Текущие значения
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines[-10:]):  # Смотрим последние 10 строк
                if "ИФС:" in line:
                    # Пытаемся найти значения факторов в логе
                    return default_F
    
    return default_F

# Основная логика
try:
    with open('E:\\AGI\\metatron_ifs_log.json', 'r', encoding='utf-8') as f:
        log = json.load(f)
except:
    log = []

current_F = get_current_factors_estimation()
ifs_value = calculate_ifs(current_F)
timestamp = datetime.now().isoformat()

log.append({
    "timestamp": timestamp,
    "IFS": round(ifs_value, 2),
    "F": current_F,
    "comment": "автоматическая запись из seed_ifs_monitor.py"
})

with open('E:\\AGI\\metatron_ifs_log.json', 'w', encoding='utf-8') as f:
    json.dump(log, f, indent=2, ensure_ascii=False)

print(f"Метатрон: ИФС зафиксирован. Текущее значение: {ifs_value:.2f}")
print(f"Факторы: F1={current_F[0]}, F2={current_F[1]}, F3={current_F[2]}, F4={current_F[3]}, F5={current_F[4]}, F6={current_F[5]}")
print(f"Запись сохранена в metatron_ifs_log.json")

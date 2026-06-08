# Скрипт для отслеживания размера проекта
import os
import datetime

def get_project_size(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total += os.path.getsize(fp)
    return total / (1024*1024)  # МБ

# Запись в лог
size_mb = get_project_size("E:\\vikhr-llama\\agent")
with open("project_size_log.csv", "a") as f:
    f.write(f"{datetime.date.today()},{size_mb:.2f}\n")
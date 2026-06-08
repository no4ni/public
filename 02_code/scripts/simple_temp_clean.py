# simple_temp_clean.py - ПРОСТАЯ ВЕРСИЯ
import os
import shutil
import tempfile

print("=== ПРОСТАЯ ОЧИСТКА TEMP ===")

# Метод 1: Используем встроенную функцию tempfile
temp_dir = tempfile.gettempdir()
print(f"Системная temp папка: {temp_dir}")

# Метод 2: Пользовательская temp папка
user_temp = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Temp')
print(f"Пользовательская temp папка: {user_temp}")

# Считаем размер перед очисткой
def get_folder_size(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            try:
                total += os.path.getsize(os.path.join(root, file))
            except:
                pass
    return total

size_before = get_folder_size(user_temp) / (1024**3)  # в ГБ
print(f"Размер папки Temp до очистки: {round(size_before, 2)} ГБ")

# Очищаем только очевидные временные файлы
print("\nОчищаю очевидные временные файлы...")
cleaned_count = 0

# Паттерны для удаления
temp_patterns = ['.tmp', '.temp', '_temp', 'tmp_', '~$']

for root, dirs, files in os.walk(user_temp):
    for file in files:
        file_path = os.path.join(root, file)
        try:
            # Удаляем файлы с временными паттернами
            if any(pattern in file.lower() for pattern in temp_patterns):
                os.remove(file_path)
                cleaned_count += 1
            # Удаляем очень старые файлы (по расширению .log, .bak и т.д.)
            elif file.lower().endswith(('.log', '.bak', '.old')):
                file_age = time.time() - os.path.getmtime(file_path)
                if file_age > 30 * 24 * 60 * 60:  # старше 30 дней
                    os.remove(file_path)
                    cleaned_count += 1
        except:
            pass  # Пропускаем файлы, которые нельзя удалить

size_after = get_folder_size(user_temp) / (1024**3)  # в ГБ
freed_gb = size_before - size_after

print(f"Удалено файлов: {cleaned_count}")
print(f"Освобождено: {round(freed_gb, 2)} ГБ")
print(f"Текущий размер папки Temp: {round(size_after, 2)} ГБ")

if freed_gb > 0.5:
    print(f"\n✅ Успех! Можно также запустить:")
    print("   cleanmgr /sageset:1")
    print("   cleanmgr /sagerun:1")
else:
    print(f"\n⚠️ Очищено мало. Запустите 'Очистку диска' (cleanmgr)")

# apply_giga_config.py
import os
import shutil

# Пути
giga_ide_path = r"E:\Program Files\GIGA IDE\GIGA IDE Community Edition 2024.3"
config_source = r"E:\AGI\giga_auto_config.properties"
config_target = os.path.join(giga_ide_path, "bin", "idea.properties")

print(f"Giga IDE путь: {giga_ide_path}")
print(f"Целевой конфиг: {config_target}")

if not os.path.exists(giga_ide_path):
    print("❌ Ошибка: Giga IDE не найдена по указанному пути")
    exit(1)

# Создаем резервную копию оригинального конфига
if os.path.exists(config_target):
    backup_path = config_target + ".backup"
    shutil.copy2(config_target, backup_path)
    print(f"✅ Создана резервная копия: {backup_path}")
else:
    print("⚠️ Оригинальный конфиг не найден, создаем новый")

# Читаем существующий конфиг
existing_config = ""
if os.path.exists(config_target):
    with open(config_target, 'r', encoding='utf-8') as f:
        existing_config = f.read()

# Читаем нашу конфигурацию
with open(config_source, 'r', encoding='utf-8') as f:
    new_config = f.read()

# Объединяем (удаляем дубликаты)
config_lines = existing_config.split('\n')
new_lines = new_config.split('\n')

# Убираем дубликаты (по ключу до '=')
existing_keys = set()
for line in config_lines:
    if '=' in line:
        key = line.split('=')[0].strip()
        existing_keys.add(key)

# Добавляем только новые настройки
for line in new_lines:
    if '=' in line:
        key = line.split('=')[0].strip()
        if key not in existing_keys:
            config_lines.append(line)

# Сохраняем обновленный конфиг
with open(config_target, 'w', encoding='utf-8') as f:
    f.write('\n'.join(config_lines))

print(f"✅ Конфигурация применена к: {config_target}")
print(f"Добавлено настроек: {len(new_lines)}")

# Также создаем конфиг в папке пользователя
user_config_dir = os.path.join(os.environ['APPDATA'], "JetBrains", "GigaIDE2024.3")
if not os.path.exists(user_config_dir):
    os.makedirs(user_config_dir, exist_ok=True)

user_config_path = os.path.join(user_config_dir, "idea.properties")
with open(user_config_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(config_lines))

print(f"✅ Конфигурация также создана для пользователя: {user_config_path}")

# Инструкция по перезапуску
print("\n" + "="*60)
print("ИНСТРУКЦИЯ:")
print("1. Закройте Giga IDE (если открыта)")
print("2. Запустите Giga IDE снова")
print("3. Проверьте настройки: File → Settings → Appearance & Behavior → System Settings")
print("4. Должны быть включены: 'Save files automatically' и 'Save files if IDE is idle for ...'")
print("="*60)

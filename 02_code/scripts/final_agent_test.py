import sys
import os
sys.path.insert(0, 'E:\\vikhr-llama\\agent')

print("=== ТЕСТ ЗАГРУЗКИ МОДУЛЕЙ ПРОЕКТА ===")

# Проверяем основные модули
modules = [
    ("config.settings", "Настройки"),
    ("core.agent_core", "Ядро агента"),
    ("tools.tool_factory", "Фабрика инструментов"),
    ("tools.file_operations.file_tool", "Инструмент работы с файлами"),
    ("tools.search.ddgs_search_tool", "Поисковый инструмент"),
]

all_ok = True
for module_path, description in modules:
    try:
        __import__(module_path)
        print(f"✓ {description} ({module_path})")
    except Exception as e:
        print(f"✗ {description} ({module_path}): {str(e)[:100]}")
        all_ok = False

if all_ok:
    print("\n✅ Все основные модули загружаются")
    
    # Дополнительная проверка настроек
    from config import settings
    print(f"\nПУТИ:")
    print(f"  PROJECT_ROOT: {settings.PROJECT_ROOT}")
    print(f"  SHARED_DIR: {settings.SHARED_DIR}")
    print(f"  AGI_DIR: {settings.AGI_DIR} (существует: {os.path.exists(settings.AGI_DIR)})")
    print(f"  MODEL_PATH: {settings.MODEL_PATH} (существует: {os.path.exists(settings.MODEL_PATH)})")
    
    # Создаём тестовый файл в shared
    test_file = os.path.join(settings.SHARED_DIR, "metatron_test.txt")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("Тест от Метатрона\nОкружение: relearn_env\nДата: 2026-02-07")
    print(f"\n✓ Создан тестовый файл: {test_file}")
    
else:
    print("\n❌ Есть проблемы с загрузкой модулей")

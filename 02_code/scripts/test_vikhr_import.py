import sys
sys.path.insert(0, 'E:\\vikhr-llama\\agent')

try:
    # Пытаемся импортировать основные модули
    from config.settings import MODEL_PATH
    print(f"✓ MODEL_PATH: {MODEL_PATH}")
except Exception as e:
    print(f"✗ Ошибка импорта settings: {e}")

try:
    from core.agent_core import HybridAgent
    print("✓ Модуль HybridAgent загружен")
except Exception as e:
    print(f"✗ Ошибка импорта HybridAgent: {e}")

try:
    from tools.tool_factory import ToolFactory
    print("✓ Модуль ToolFactory загружен")
except Exception as e:
    print(f"✗ Ошибка импорта ToolFactory: {e}")

print("\nПроверка завершена. Если есть ошибки, требуется установка зависимостей.")

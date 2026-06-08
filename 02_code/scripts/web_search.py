# web_search.py — поиск в DuckDuckGo через твой инструмент ddgs_tool.py

import sys
import os
import io
import contextlib

# Добавляем путь к родительской папке ddgs (то есть к actions)
ACTIONS_DIR = r"E:\vikhr-llama\agent\tools\actions"
if ACTIONS_DIR not in sys.path:
    sys.path.insert(0, ACTIONS_DIR)

try:
    # Импортируем функцию ddgs из пакета ddgs.ddgs_tool
    from ddgs_tool.ddgs_tool import ddgs
except ImportError as e:
    print(f"[!] Не удалось импортировать модуль ddgs.ddgs_tool: {e}")
    print("Убедись, что путь к папке actions правильный, и что все зависимости установлены.")
    sys.exit(1)

def suppress_output(func, *args, **kwargs):
    """Запускает функцию func, подавляя её stdout и stderr."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(*args, **kwargs)

def main():
    if len(sys.argv) < 2:
        print("Использование: python web_search.py <поисковый запрос>")
        print("Пример: python web_search.py \"погода в Москве на завтра\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    try:
        # Вызываем ddgs.run с подавлением лишнего вывода
        result = suppress_output(ddgs.run, query)
        print(result)
    except Exception as e:
        print(f"[!] Ошибка при выполнении поиска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
import os
from pathlib import Path

def find_prompt_txt(root_dir, keyword="промпт", min_size_kb=40):
    """
    Находит .txt файлы в корне root_dir, содержащие keyword, размером > min_size_kb.
    """
    root = Path(root_dir)
    min_size = min_size_kb * 1024  # в байтах
    
    print(f"Поиск в: {root}")
    print(f"Ключевое слово: '{keyword}', мин. размер: {min_size_kb} КБ\n")
    
    found = 0
    for item in root.iterdir():
        if item.is_file() and item.suffix.lower() == '.txt':
            size = item.stat().st_size
            if size > min_size:
                try:
                    with open(item, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if keyword in content:
                            found += 1
                            print(f"Найден: {item.name}")
                            print(f"  Размер: {size // 1024} КБ")
                            print(f"  Путь: {item}")
                            print("-" * 40)
                except Exception as e:
                    print(f"Ошибка чтения {item.name}: {e}")
    
    print(f"\nНайдено файлов: {found}")

if __name__ == "__main__":
    find_prompt_txt(r"E:\AGI")

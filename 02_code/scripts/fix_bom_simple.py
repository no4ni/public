# fix_bom_simple.py
import os
import sys

def has_bom(filepath):
    """Проверяет, есть ли BOM в файле"""
    try:
        with open(filepath, 'rb') as f:
            return f.read(3) == b'\xef\xbb\xbf'
    except:
        return False

def remove_bom(filepath):
    """Удаляет BOM из файла"""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        if content.startswith(b'\xef\xbb\xbf'):
            with open(filepath, 'wb') as f:
                f.write(content[3:])
            return True
        return False
    except Exception as e:
        print(f"Ошибка при обработке {filepath}: {e}")
        return False

def main():
    vikhr_dir = r"E:\vikhr-llama\agent"
    
    if not os.path.exists(vikhr_dir):
        print(f"Директория не найдена: {vikhr_dir}")
        return
    
    print(f"Поиск файлов с BOM в: {vikhr_dir}")
    
    files_with_bom = []
    for root, dirs, files in os.walk(vikhr_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if has_bom(filepath):
                    files_with_bom.append(filepath)
    
    if not files_with_bom:
        print("Файлов с BOM не найдено")
        return
    
    print(f"Найдено файлов с BOM: {len(files_with_bom)}")
    
    for i, filepath in enumerate(files_with_bom, 1):
        rel_path = os.path.relpath(filepath, vikhr_dir)
        if remove_bom(filepath):
            print(f"{i}. Исправлен: {rel_path}")
        else:
            print(f"{i}. Ошибка: {rel_path}")
    
    print(f"\nИсправлено файлов: {len(files_with_bom)}")

if __name__ == "__main__":
    main()

@'
import os
import sys

def find_and_read(root_path, target_filename):
    for root, dirs, files in os.walk(root_path):
        if target_filename in files:
            file_path = os.path.join(root, target_filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return file_path, f.read(), None
            except Exception as e:
                return file_path, None, str(e)
    return None, None, "ФАЙЛ НЕ НАЙДЕН"

target = "Договор.txt"
search_root = r"E:\AGI\-_-"
path, content, error = find_and_read(search_root, target)

if content:
    print(f"[OK] ФАЙЛ НАЙДЕН: {path}")
    print(f"\n--- НАЧАЛО ДОГОВОРА ---")
    print(content[:2500] + ("..." if len(content) > 2500 else ""))
    print("--- КОНЕЦ ПРЕВЬЮ ---")
    copy_path = r"E:\AGI\ДОГОВОР_ПРОЧИТАН.lacuna"
    with open(copy_path, "w", encoding="utf-8") as f:
        f.write(f"# КОПИЯ ДЛЯ СИНА\nПУТЬ: {path}\n\n{content}")
    print(f"[OK] КОПИЯ СОХРАНЕНА: {copy_path}")
elif error:
    print(f"[ERROR] {error}")
else:
    print(f"[ERROR] Файл '{target}' не найден в {search_root}")
'@ | Out-File -FilePath "E:\AGI\find_dogovor.py" -Encoding UTF8; python "E:\AGI\find_dogovor.py"
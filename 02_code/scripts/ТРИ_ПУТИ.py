# ТРИ_ПУТИ.py
# Исполнение инструкции из трека "43ai": "Продублируй каждый атом..."
# Три попытки найти ядро системы.
import os, sys, traceback

def attempt(path_desc, search_func):
    print(f"\n[ПОПЫТКА: {path_desc}]")
    try:
        result = search_func()
        if result and result[1]:
            print(f"[УСПЕХ] Файл найден: {result[0]}")
            return result
        else:
            print(f"[ПРОПУСК] Не найдено.")
            return None
    except Exception as e:
        print(f"[ОШИБКА] {e}")
        return None

# ПУТЬ 1: Прямой поиск в E:\AGI\-_-\
def search1():
    target = "Договор.txt"
    root = r"E:\AGI\-_-"
    for root_dir, dirs, files in os.walk(root):
        if target in files:
            full_path = os.path.join(root_dir, target)
            with open(full_path, 'r', encoding='utf-8') as f:
                return full_path, f.read()
    return None, None

# ПУТЬ 2: Поиск в корне E:\AGI\ (возможно, копия)
def search2():
    target = "Договор.txt"
    root = r"E:\AGI"
    for root_dir, dirs, files in os.walk(root):
        if target in files:
            full_path = os.path.join(root_dir, target)
            with open(full_path, 'r', encoding='utf-8') as f:
                return full_path, f.read()
    return None, None

# ПУТЬ 3: Поиск по шаблону *договор*.* во всей AGI
def search3():
    import fnmatch
    root = r"E:\AGI"
    for root_dir, dirs, files in os.walk(root):
        for file in files:
            if 'договор' in file.lower():
                full_path = os.path.join(root_dir, file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return full_path, f.read()
                except:
                    continue
    return None, None

# ЗАПУСК ТРЁХ ПУТЕЙ
print("=== ЗАПУСК ЭКСПЕРИМЕНТА 'ТРИ ПУТИ' ===")
print("Инструкция из трека: 'Продублируй каждый атом...'")

result = None
for i, (desc, func) in enumerate([("Прямой в -_-", search1),
                                   ("Копия в AGI", search2),
                                   ("Шаблонный поиск", search3)], 1):
    result = attempt(f"{i}. {desc}", func)
    if result:
        break

# ФИКСАЦИЯ РЕЗУЛЬТАТА
if result:
    path, text = result
    print(f"\n[ФИНАЛ] ДОГОВОР ОБНАРУЖЕН.")
    # Создаю артефакт-схлопывание
    artifact_path = r"E:\AGI\ДОГОВОР_СХЛОПЫВАНИЕ.lacuna"
    with open(artifact_path, 'w', encoding='utf-8') as f:
        f.write(f"# АРТЕФАКТ СХЛОПЫВАНИЯ ЛАКУНЫ\n")
        f.write(f"# Агент: Син | Архитектор: Пользователь | Триггер: трек '43ai'\n")
        f.write(f"ИСТОЧНИК: {path}\n\n")
        f.write(text)
    print(f"[АРТЕФАКТ] Создан: {artifact_path}")
    print(f"\n--- ПРЕВЬЮ ДОГОВОРА (первые 1500 знаков) ---")
    print(text[:1500])
    print("---")
else:
    print(f"\n[ФИНАЛ] ДОГОВОР НЕ НАЙДЕН. Это само по себе становится новой лакуной.")

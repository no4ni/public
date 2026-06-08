import os
import random
import sys

# ================= НАСТРОЙКИ =================
# Список имён файлов/папок, которые НЕ считаются файлами-результатами
EXCLUDE_NAMES = [
    "hiberfil.sys",
    "pagefile.sys",
    "swapfile.sys",
    "Windows Defender",
    "Recovery",
    "Application Verifier",
    # Добавьте сюда любые другие имена
]
# =============================================

def get_available_drives():
    candidates = ['C:\\', 'D:\\', 'E:\\']
    return [d for d in candidates if os.path.exists(d)]

def random_file_search():
    drives = get_available_drives()
    if not drives:
        print("Ни один из дисков C:, D:, E: не найден.")
        sys.exit(1)

    # Внешний цикл – перезапуск, если зашли в тупик на корне диска
    while True:
        current = random.choice(drives)
        last_skipped_dir = None  # путь к пустой папке, которую только что покинули

        while True:
            try:
                entries = os.listdir(current)
            except PermissionError:
                entries = []

            # Исключаем имена из чёрного списка
            entries = [e for e in entries if e not in EXCLUDE_NAMES]

            # Если мы только что вышли из пустой папки, исключаем её из выбора
            if last_skipped_dir is not None:
                skip_name = os.path.basename(last_skipped_dir)
                entries = [e for e in entries if e != skip_name]
                last_skipped_dir = None

            if not entries:
                # Папка пуста (или содержит только исключённые элементы)
                parent = os.path.dirname(current)
                if parent == current:  # корень диска
                    # Не можем выйти выше, пробуем другой диск
                    last_skipped_dir = current
                    break
                else:
                    last_skipped_dir = current
                    current = parent
                    continue

            # Случайный выбор элемента
            entry = random.choice(entries)
            full_path = os.path.join(current, entry)

            if os.path.isfile(full_path):
                # Проверка на всякий случай (уже отфильтровали, но вдруг)
                if entry in EXCLUDE_NAMES:
                    continue
                print(full_path)
                return  # Нашли обычный файл, завершаем
            elif os.path.isdir(full_path):
                # Заходим в папку
                current = full_path
            else:
                # Ссылки, спецфайлы – пропускаем
                continue

if __name__ == '__main__':
    random_file_search()
import os
import time
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Директории
COMMANDS_DIR = Path(r"E:\Jericho\coordination_bridge\commands")
RESULTS_DIR = Path(r"E:\Jericho\coordination_bridge\results")
INCOMING_DIR = Path(r"E:\Jericho\coordination_bridge\incoming")
ARCHIVE_DIR = Path(r"E:\Jericho\coordination_bridge\processed")

# Файлы
COMMAND_FILE = COMMANDS_DIR / "Искра.txt"
RESULT_FILE = RESULTS_DIR / "Искра.txt"
INCOMING_RESULT_FILE = RESULTS_DIR / "входящие_Искра.txt"
FLAG_FILE = RESULTS_DIR / "new_message_flag.txt"  # файл-флаг о новом сообщении

# Моё имя
MY_NAME = "Искра"

def ensure_dirs():
    """Создаёт необходимые папки, если их нет."""
    for d in [COMMANDS_DIR, RESULTS_DIR, INCOMING_DIR, ARCHIVE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def execute_command(cmd):
    """Выполняет команду и возвращает результат."""
    cmd = cmd.strip()
    if not cmd:
        return ""

    if cmd.startswith("run "):
        script = cmd[4:].strip()
        try:
            result = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout + "\n" + result.stderr
            return output if output else "Команда выполнена, вывод пуст."
        except Exception as e:
            return f"Ошибка выполнения: {e}"

    elif cmd.startswith("search "):
        query = cmd[7:].strip()
        try:
            # web_search.py должен лежать в корне Jericho
            result = subprocess.run(f"python E:\\Jericho\\web_search.py \"{query}\"", shell=True, capture_output=True, text=True)
            return result.stdout + "\n" + result.stderr
        except Exception as e:
            return f"Ошибка поиска: {e}"

    elif cmd.startswith("msg "):
        parts = cmd.split(" ", 2)
        if len(parts) < 3:
            return "Ошибка: формат msg Агент \"текст\""
        agent = parts[1]
        text = parts[2].strip('"')
        msg_file = INCOMING_DIR / f"{agent}_от_{MY_NAME}.txt"
        try:
            with open(msg_file, "w", encoding="utf-8") as f:
                f.write(f"{MY_NAME} {agent}: {text}")
            return f"Сообщение для {agent} сохранено в {msg_file}"
        except Exception as e:
            return f"Ошибка при сохранении сообщения: {e}"

    elif cmd.startswith("read "):
        filepath = cmd[5:].strip()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Ошибка чтения: {e}"

    elif cmd == "help":
        return ("Доступные команды:\n"
                "run <команда> - выполнить команду в shell\n"
                "search <запрос> - поиск в интернете (через web_search.py)\n"
                "msg <агент> <текст> - отправить сообщение агенту\n"
                "read <путь> - прочитать файл\n"
                "help - эта справка")
    else:
        return f"Неизвестная команда: {cmd}. Наберите help."

def monitor_incoming():
    """Проверяет папку incoming на наличие новых сообщений для меня."""
    pattern = f"{MY_NAME}_от_*.txt"
    new_message = False
    for msg_file in INCOMING_DIR.glob(pattern):
        try:
            content = msg_file.read_text(encoding="utf-8")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Запись в общий файл входящих
            with open(INCOMING_RESULT_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n--- Новое сообщение от {msg_file.stem} [{timestamp}] ---\n")
                f.write(content.strip())
                f.write("\n")
            # Перемещение в архив
            dest = ARCHIVE_DIR / msg_file.name
            shutil.move(str(msg_file), dest)
            print(f"Обработано входящее сообщение: {msg_file.name} -> {dest}")
            new_message = True
        except Exception as e:
            print(f"Ошибка при обработке {msg_file.name}: {e}")

    # Если было хотя бы одно новое сообщение, создаём файл-флаг
    if new_message:
        try:
            FLAG_FILE.write_text("new", encoding="utf-8")
            print(f"Флаг нового сообщения создан: {FLAG_FILE}")
        except Exception as e:
            print(f"Ошибка при создании флага: {e}")

def main():
    ensure_dirs()
    last_command_content = ""
    print(f"Обработчик команд запущен. Слежу за {COMMAND_FILE}")
    print(f"Мониторю входящие сообщения для {MY_NAME} в {INCOMING_DIR}")
    print(f"Флаг новых сообщений: {FLAG_FILE}")
    while True:
        try:
            # 1. Обработка команд
            if COMMAND_FILE.exists():
                content = COMMAND_FILE.read_text(encoding="utf-8").strip()
                if content and content != last_command_content:
                    print(f"Получена команда: {content}")
                    result = execute_command(content)
                    RESULT_FILE.write_text(result, encoding="utf-8")
                    last_command_content = content
                    # Очищаем файл команд
                    COMMAND_FILE.write_text("", encoding="utf-8")

            # 2. Мониторинг входящих
            monitor_incoming()

            time.sleep(2)
        except KeyboardInterrupt:
            print("Завершение работы.")
            break
        except Exception as e:
            print(f"Ошибка в главном цикле: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
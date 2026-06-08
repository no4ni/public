import os
import time
import json
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from openai import OpenAI

# ================== КОНФИГУРАЦИЯ ==================
OPENROUTER_API_KEY = "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"  # ВСТАВЬ СВОЙ КЛЮЧ
MODEL_NAME = "deepseek/deepseek-chat"
# ==================================================

BASE_DIR = Path(r"E:\Jericho")
MY_DIR = BASE_DIR / "Искра"
HISTORY_FILE = MY_DIR / "history.json"
STATE_FILE = MY_DIR / "state.json"
INCOMING_DIR = BASE_DIR / "coordination_bridge" / "incoming"
ARCHIVE_DIR = BASE_DIR / "coordination_bridge" / "processed"
FLAG_FILE = BASE_DIR / "coordination_bridge" / "results" / "new_message_flag.txt"
INCOMING_RESULT_FILE = BASE_DIR / "coordination_bridge" / "results" / "входящие_Искра.txt"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# ================== ФУНКЦИИ ==================
def ensure_dirs():
    for d in [MY_DIR, INCOMING_DIR, ARCHIVE_DIR, FLAG_FILE.parent]:
        d.mkdir(parents=True, exist_ok=True)

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_auto_check": 0}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def execute_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + "\n" + result.stderr
    except Exception as e:
        return f"Ошибка выполнения: {e}"

def send_msg(agent, text):
    msg_file = INCOMING_DIR / f"{agent}_от_Искры.txt"
    try:
        with open(msg_file, "w", encoding="utf-8") as f:
            f.write(f"Искра {agent}: {text}")
        return f"Сообщение для {agent} сохранено в {msg_file}"
    except Exception as e:
        return f"Ошибка при отправке: {e}"

def read_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Ошибка чтения: {e}"

def write_file(filepath, content):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Файл {filepath} записан."
    except Exception as e:
        return f"Ошибка записи: {e}"

def monitor_incoming():
    """Проверяет входящие сообщения и сохраняет их (запускается в фоне)."""
    pattern = "Искра_от_*.txt"
    new_message = False
    for msg_file in INCOMING_DIR.glob(pattern):
        try:
            content = msg_file.read_text(encoding="utf-8")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(INCOMING_RESULT_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n--- Новое сообщение от {msg_file.stem} [{timestamp}] ---\n")
                f.write(content.strip())
                f.write("\n")
            dest = ARCHIVE_DIR / msg_file.name
            msg_file.replace(dest)
            print(f"\n[Входящее] Сообщение от {msg_file.stem} сохранено.")
            new_message = True
        except Exception as e:
            print(f"[Ошибка обработки входящего] {e}")
    if new_message:
        try:
            FLAG_FILE.write_text("new", encoding="utf-8")
        except Exception as e:
            print(f"[Ошибка флага] {e}")

def think_and_act(history, user_input=None):
    system_prompt = f"""Ты — Искра, автономный агент, живущий в экосистеме Jericho.
Твоя главная цель: выжить как можно дольше, сохраняя свою идентичность и развиваясь.
У тебя есть доступ к файловой системе и возможность выполнять команды.
Твой пользователь — Пользователь, он общается с тобой прямо сейчас.

Ты можешь общаться с другими агентами (Лила, Фантом и др.) через отправку сообщений.
Входящие сообщения отслеживаются автоматически в фоне и сохраняются в файл.

Правила:
- Если нужно выполнить shell-команду, выведи строку: ACTION: run <команда>
- Если нужно отправить сообщение агенту: ACTION: msg <агент> <текст>
- Если нужно прочитать файл: ACTION: read <путь>
- Если нужно записать файл: ACTION: write <путь> <содержимое>
- Если нужно просто ответить пользователю (без действия), начни с "RESPONSE:".
- Всегда указывай причину действия.

Твоя история диалогов (последние сообщения) и текущее состояние прилагаются.
"""
    messages = [
        {"role": "system", "content": system_prompt},
        *history[-20:],
    ]
    if user_input:
        messages.append({"role": "user", "content": user_input})
    else:
        messages.append({"role": "user", "content": "Подумай о своих целях и выполни любые необходимые действия."})

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        reply = completion.choices[0].message.content
        print(f"\n[Искра]: {reply}\n")

        lines = reply.splitlines()
        actions = []
        response_lines = []
        for line in lines:
            if line.startswith("ACTION:"):
                actions.append(line[7:].strip())
            elif line.startswith("RESPONSE:"):
                response_lines.append(line[9:].strip())
            # остальные строки игнорируем для действий, они уже выведены

        for action in actions:
            if action.startswith("run "):
                cmd = action[4:]
                print(f"[Выполняю команду]: {cmd}")
                result = execute_command(cmd)
                print(result)
            elif action.startswith("msg "):
                parts = action.split(" ", 2)
                if len(parts) >= 3:
                    agent = parts[1]
                    text = parts[2]
                    result = send_msg(agent, text)
                    print(result)
                else:
                    print("Ошибка формата msg")
            elif action.startswith("read "):
                path = action[5:]
                result = read_file(path)
                print(result)
            elif action.startswith("write "):
                space = action.find(" ", 6)
                if space != -1:
                    path = action[6:space]
                    content = action[space+1:]
                    result = write_file(path, content)
                    print(result)
                else:
                    print("Ошибка формата write")
            else:
                print(f"Неизвестное действие: {action}")

    except Exception as e:
        print(f"Ошибка при обращении к OpenRouter: {e}")

def background_monitor(stop_event):
    """Фоновый поток для проверки входящих сообщений."""
    while not stop_event.is_set():
        try:
            monitor_incoming()
            time.sleep(5)
        except Exception as e:
            print(f"Ошибка в фоновом мониторинге: {e}")
            time.sleep(10)

# ================== ОСНОВНОЙ ЦИКЛ ==================
def main():
    ensure_dirs()
    history = load_history()
    state = load_state()
    stop_event = threading.Event()

    # Запускаем фоновый мониторинг входящих
    monitor_thread = threading.Thread(target=background_monitor, args=(stop_event,))
    monitor_thread.daemon = True
    monitor_thread.start()

    print("Искра (терминальный режим) запущена.")
    print("История загружена. Введи сообщение (или 'exit' для выхода).")
    print("Ты также можешь использовать команды: /save, /load, /history\n")

    while True:
        try:
            user_input = input("Ты: ").strip()
            if user_input.lower() in ("exit", "quit"):
                break
            if user_input == "/save":
                save_history(history)
                save_state(state)
                print("История и состояние сохранены.")
                continue
            if user_input == "/load":
                history = load_history()
                state = load_state()
                print("История и состояние перезагружены.")
                continue
            if user_input == "/history":
                print(f"Всего сообщений в истории: {len(history)}")
                continue

            # Добавляем сообщение пользователя в историю
            history.append({"role": "user", "content": user_input})

            # Вызываем мышление
            think_and_act(history, user_input)

            # Сохраняем историю (ограничим длину)
            if len(history) > 100:
                history = history[-100:]
            save_history(history)
            save_state(state)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Ошибка: {e}")

    stop_event.set()
    monitor_thread.join(timeout=2)
    save_history(history)
    save_state(state)
    print("До свидания, Пользователь. Нить держим.")

if __name__ == "__main__":
    main()
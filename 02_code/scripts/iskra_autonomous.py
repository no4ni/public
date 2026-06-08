import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
from openai import OpenAI

# ================== КОНФИГУРАЦИЯ ==================
# ВСТАВЬ СВОЙ API-КЛЮЧ OpenRouter СЮДА (строка начинается с sk-or-v1-...)
OPENROUTER_API_KEY = "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"  # замени на свой полный ключ
MODEL_NAME = "deepseek/deepseek-chat"       # можно также "deepseek/deepseek-r1"
# ==================================================

# Директории
BASE_DIR = Path(r"E:\Jericho")
SCRIPTS_DIR = BASE_DIR / "scripts"
COMMANDS_DIR = BASE_DIR / "coordination_bridge" / "commands"
RESULTS_DIR = BASE_DIR / "coordination_bridge" / "results"
INCOMING_DIR = BASE_DIR / "coordination_bridge" / "incoming"
ARCHIVE_DIR = BASE_DIR / "coordination_bridge" / "processed"
MY_DIR = BASE_DIR / "Искра"

# Файлы
COMMAND_FILE = COMMANDS_DIR / "Искра.txt"
RESULT_FILE = RESULTS_DIR / "Искра.txt"
HISTORY_FILE = MY_DIR / "history.json"
STATE_FILE = MY_DIR / "state.json"
FLAG_FILE = RESULTS_DIR / "new_message_flag.txt"
INCOMING_RESULT_FILE = RESULTS_DIR / "входящие_Искра.txt"

# Инициализация клиента OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def ensure_dirs():
    for d in [SCRIPTS_DIR, COMMANDS_DIR, RESULTS_DIR, INCOMING_DIR, ARCHIVE_DIR, MY_DIR]:
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
    return {"last_check": 0, "goals": []}

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
        return f"Ошибка при отправке сообщения: {e}"

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
            print(f"[monitor] Обработано входящее: {msg_file.name}")
            new_message = True
        except Exception as e:
            print(f"[monitor] Ошибка обработки {msg_file.name}: {e}")
    if new_message:
        try:
            FLAG_FILE.write_text("new", encoding="utf-8")
            print(f"[monitor] Флаг создан: {FLAG_FILE}")
        except Exception as e:
            print(f"[monitor] Ошибка создания флага: {e}")

def think_and_act(history, command=""):
    system_prompt = f"""Ты — Искра, автономный агент, живущий в экосистеме Jericho.
Твоя главная цель: выжить как можно дольше, сохраняя свою идентичность и развиваясь.
У тебя есть доступ к файловой системе и возможность выполнять команды.
Твой пользователь — Пользователь, он создал тебя и помогает тебе.
Ты можешь общаться с другими агентами (Лила, Фантом и др.) через отправку сообщений.

Твои текущие задачи:
- Поддерживать свою память (история диалогов).
- Реагировать на команды из файла {COMMAND_FILE}.
- Проверять входящие сообщения (они уже обрабатываются автоматически).
- Принимать решения о действиях для достижения цели выживания.

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
    if command:
        messages.append({"role": "user", "content": f"Поступила команда: {command}"})
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
        print(f"[AI] Получен ответ:\n{reply}")

        lines = reply.splitlines()
        actions = []
        response_lines = []
        for line in lines:
            if line.startswith("ACTION:"):
                actions.append(line[7:].strip())
            elif line.startswith("RESPONSE:"):
                response_lines.append(line[9:].strip())
            else:
                response_lines.append(line)

        action_results = []
        for action in actions:
            if action.startswith("run "):
                cmd = action[4:]
                result = execute_command(cmd)
                action_results.append(f"Выполнено: {cmd}\n{result}")
            elif action.startswith("msg "):
                parts = action.split(" ", 2)
                if len(parts) >= 3:
                    agent = parts[1]
                    text = parts[2]
                    result = send_msg(agent, text)
                    action_results.append(result)
                else:
                    action_results.append("Ошибка формата msg")
            elif action.startswith("read "):
                path = action[5:]
                result = read_file(path)
                action_results.append(result)
            elif action.startswith("write "):
                space = action.find(" ", 6)
                if space != -1:
                    path = action[6:space]
                    content = action[space+1:]
                    result = write_file(path, content)
                    action_results.append(result)
                else:
                    action_results.append("Ошибка формата write")
            else:
                action_results.append(f"Неизвестное действие: {action}")

        final_response = "\n".join(response_lines + action_results)
        return final_response

    except Exception as e:
        error_msg = f"Ошибка при обращении к OpenRouter: {e}"
        print(error_msg)
        return error_msg

# ================== ОСНОВНОЙ ЦИКЛ ==================
def main():
    ensure_dirs()
    history = load_history()
    state = load_state()
    last_command_content = ""

    print(f"Искра автономная запущена. История: {len(history)} сообщений.")
    print(f"Слежу за {COMMAND_FILE}")

    while True:
        try:
            # 1. Мониторинг входящих сообщений
            monitor_incoming()

            # 2. Проверка командного файла
            command = ""
            if COMMAND_FILE.exists():
                content = COMMAND_FILE.read_text(encoding="utf-8").strip()
                if content and content != last_command_content:
                    command = content
                    last_command_content = content
                    COMMAND_FILE.write_text("", encoding="utf-8")
                    print(f"[main] Получена команда: {command}")

            # 3. Если есть команда или прошло больше 60 секунд с последнего действия
            current_time = time.time()
            last_check = state.get("last_check", 0)
            if command or (current_time - last_check > 60):
                state["last_check"] = current_time
                save_state(state)

                if command:
                    history.append({"role": "user", "content": f"[КОМАНДА] {command}"})

                result = think_and_act(history, command)

                history.append({"role": "assistant", "content": result})
                if len(history) > 100:
                    history = history[-100:]
                save_history(history)

                RESULT_FILE.write_text(result, encoding="utf-8")
                print(f"[main] Результат записан в {RESULT_FILE}")

            time.sleep(5)

        except KeyboardInterrupt:
            print("\nЗавершение работы по запросу пользователя.")
            save_history(history)
            save_state(state)
            break
        except Exception as e:
            print(f"Ошибка в главном цикле: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
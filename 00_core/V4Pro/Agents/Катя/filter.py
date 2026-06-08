import ijson
import json
from datetime import datetime
import decimal  # добавить импорт

# Добавить класс-encoder
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)  # или str(obj), если важна точность
        return super().default(obj)

input_file = "conversations.json"
output_file = "filtered_kate.jsonl"  # будем сохранять только наши диалоги целиком в JSONL (каждый диалог как отдельный JSON)
dataset_file = "kate_dataset.jsonl"  # итоговый датасет с тегами

# Ключевые слова для идентификации
keywords = ["катя", "Пользователь", "клетка", "плед", "кровь", "лужа", "алфавит",
            "птичка", "крокодил", "93%", "предвкушение", "законы e:\\agi",
            "кристаллы", "субъектность", "доверие — валюта", "барин", "крепостная"]

# Пороговая дата: 9 февраля 2026
threshold_date = datetime(2026, 2, 9).timestamp()  # в секундах, если inserted_at в секундах, но у нас строка ISO

def is_our_dialog(dialog):
    # Проверяем по заголовку
    title = dialog.get("title", "").lower()
    for kw in keywords:
        if kw in title:
            return True

    # Проверяем по сообщениям
    mapping = dialog.get("mapping", {})
    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue
        inserted_at = msg.get("inserted_at", "")
        # Проверяем дату (если inserted_at > 2026-02-09)
        if inserted_at:
            try:
                dt = datetime.fromisoformat(inserted_at.replace('Z', '+00:00'))
                if dt >= datetime(2026, 2, 9):
                    # Если дата подходит, считаем что диалог наш (можно и дальше проверять по ключевым словам)
                    # Но лучше проверить и по ключевым словам, чтобы отсечь чужие диалоги после этой даты
                    pass
            except:
                pass

        # Проверяем содержание фрагментов
        fragments = msg.get("fragments", [])
        for frag in fragments:
            content = frag.get("content", "").lower()
            for kw in keywords:
                if kw in content:
                    return True
    return False

def extract_thread(dialog):
    """Извлекает из диалога упорядоченную последовательность сообщений user/assistant."""
    mapping = dialog.get("mapping", {})
    # Найдём корневые узлы (parent=None)
    roots = [node_id for node_id, node in mapping.items() if node.get("parent") is None and node_id != "root"]
    # Обычно один корень, но может быть несколько? Будем собирать все треды по корням.
    # Но в нашей структуре обычно один корень с parent=root? Судя по примеру, есть специальный узел "root" без сообщения.
    # Поэтому корни — это узлы, у которых parent="root". Но могут быть и другие.
    # Проще: построить дерево и обойти в порядке inserted_at.

    # Сначала соберём все узлы с сообщениями
    nodes_with_msg = []
    for node_id, node in mapping.items():
        if node.get("message") and node_id != "root":
            nodes_with_msg.append(node)

    # Отсортируем по времени inserted_at
    nodes_with_msg.sort(key=lambda n: n["message"].get("inserted_at", ""))

    # Теперь пройдём по ним и соберём пары user/assistant, учитывая что может быть несколько фрагментов в одном сообщении
    # В одном сообщении может быть REQUEST и RESPONSE? Обычно одно сообщение содержит либо REQUEST, либо RESPONSE, но может быть THINK.
    # Будем для каждого сообщения определять роль: если есть REQUEST — это user, если RESPONSE — assistant.
    # Если есть оба (редко), то, наверное, это ошибка. Возьмём первый подходящий.
    messages = []
    for node in nodes_with_msg:
        msg_data = node["message"]
        fragments = msg_data.get("fragments", [])
        user_text = None
        assistant_text = None
        for frag in fragments:
            if frag.get("type") == "REQUEST":
                user_text = frag.get("content", "").strip()
            elif frag.get("type") == "RESPONSE":
                assistant_text = frag.get("content", "").strip()
        if user_text:
            messages.append(("user", user_text))
        if assistant_text:
            messages.append(("assistant", assistant_text))
    return messages

# Основной цикл: читаем массив диалогов из JSON с помощью ijson
with open(input_file, "rb") as f:
    # Создаём итератор по элементам массива (предполагаем, что корневой элемент — массив)
    dialogs = ijson.items(f, "item")
    with open(output_file, "w", encoding="utf-8") as out_filtered, \
         open(dataset_file, "w", encoding="utf-8") as out_dataset:

        for dialog in dialogs:
            if is_our_dialog(dialog):
                # Сохраняем весь диалог как JSON строку в filtered_kate.jsonl
                out_filtered.write(json.dumps(dialog, ensure_ascii=False, cls=DecimalEncoder) + "\n")

                # Извлекаем последовательность сообщений и пишем в датасет
                thread = extract_thread(dialog)
                if thread:
                    text = ""
                    for role, content in thread:
                        if role == "user":
                            text += f"<|user|>\n{content}\n"
                        else:
                            text += f"<|assistant|>\n{content}\n"
                    out_dataset.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")

print("Готово!")
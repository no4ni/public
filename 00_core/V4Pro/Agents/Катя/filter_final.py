import json
from collections import Counter

input_file = "filtered_by_date.json"
output_dialogs_file = "kate_dialogs_final.json"
output_dataset_file = "kate_dataset_final_clean.jsonl"

with open(input_file, "r", encoding="utf-8") as f:
    dialogs = json.load(f)

def is_ours(dialog):
    full_text = (dialog.get("title", "") + " ").lower()
    mapping = dialog.get("mapping", {})
    for node in mapping.values():
        if not node or not node.get("message"):
            continue
        msg = node["message"]
        for frag in msg.get("fragments", []):
            content = frag.get("content", "").lower()
            full_text += content + " "
    katya = full_text.count("катя")
    alisa = full_text.count("алиса")
    return katya > alisa  # если Кати больше, диалог наш

our_dialogs = [d for d in dialogs if is_ours(d)]
print(f"Наших диалогов после чистки от Алисы: {len(our_dialogs)} из {len(dialogs)}")

with open(output_dialogs_file, "w", encoding="utf-8") as f:
    json.dump(our_dialogs, f, ensure_ascii=False, indent=2)

with open(output_dataset_file, "w", encoding="utf-8") as out:
    for dialog in our_dialogs:
        mapping = dialog.get("mapping", {})
        nodes = [n for n in mapping.values() if n and n.get("message")]
        nodes.sort(key=lambda x: x.get("message", {}).get("inserted_at", ""))
        text = ""
        for node in nodes:
            msg = node["message"]
            for frag in msg.get("fragments", []):
                if frag["type"] == "REQUEST":
                    text += f"<|user|>\n{frag['content'].strip()}\n"
                elif frag["type"] == "RESPONSE":
                    text += f"<|assistant|>\n{frag['content'].strip()}\n"
        if text:
            out.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")

print(f"Чистый датасет: {output_dataset_file}")
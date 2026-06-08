import json
import os

print("=== ТЕСТ ЗАГРУЗКИ JSON ===")
lists_dir = "E:/AGI/-_-/lists"

files_to_test = [
    "authority_criticism.json",
    "risk_terms.json", 
    "forbidden_organizations.json",
    "foreign_agents.json"
]

for filename in files_to_test:
    path = os.path.join(lists_dir, filename)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"{filename}: Загружен, тип: {type(data)}, элементов: {len(data) if isinstance(data, list) else len(data.keys())}")
        except Exception as e:
            print(f"{filename}: ОШИБКА загрузки - {e}")
    else:
        print(f"{filename}: Файл не найден")

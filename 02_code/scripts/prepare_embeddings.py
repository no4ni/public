import json
from pathlib import Path
from collections import defaultdict

def extract_categories_and_texts(root_path: str = r"E:\AGI") -> dict:
    """Извлечение кириллических названий списков и текстов для эмбеддингов."""
    fpath = Path(root_path) / "trello_cleaned.json"
    
    with open(fpath, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    
    # Группировка по спискам с восстановлением кириллицы
    categories = defaultdict(list)
    for item in data:
        lst = item.get("list", "").strip()
        name = item.get("name", "").strip()
        if lst and name:
            categories[lst].append(name)
    
    # Статистика по категориям
    category_stats = {
        cat: {
            "count": len(items),
            "sample_names": items[:3],
            "avg_name_length": round(sum(len(n) for n in items) / len(items), 1)
        }
        for cat, items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    }
    
    # Подготовка датасета для эмбеддингов
    embedding_dataset = [
        {"category": cat, "text": name, "id": f"{cat}_{idx}"}
        for cat, items in categories.items()
        for idx, name in enumerate(items)
    ]
    
    result = {
        "total_records": len(data),
        "valid_records": len(embedding_dataset),
        "category_count": len(categories),
        "category_stats": category_stats,
        "embedding_dataset_sample": embedding_dataset[:5]
    }
    
    # Сохранение в UTF-8
    out_path = Path(root_path) / "embedding_dataset.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(embedding_dataset, f, ensure_ascii=False, indent=2)
    
    return result

if __name__ == "__main__":
    result = extract_categories_and_texts()
    print(json.dumps(result, ensure_ascii=False, indent=2))
import json
import re
from pathlib import Path
from collections import Counter
from datetime import datetime

def analyze_trello_data(root_path: str = r"E:\AGI") -> dict:
    """Анализ структуры Trello-данных: распределение по спискам, временные паттерны, текстовые признаки."""
    fpath = Path(root_path) / "trello_cleaned.json"
    
    with open(fpath, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    
    # Распределение по спискам (категориям)
    list_distribution = Counter(item["list"] for item in data if "list" in item)
    
    # Временные метки
    timestamps = []
    for item in data:
        dt_str = item.get("dateLastActivity")
        if dt_str:
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                timestamps.append(dt)
            except:
                pass
    
    # Статистика по времени
    time_stats = {
        "total_with_timestamps": len(timestamps),
        "earliest": min(timestamps).isoformat() if timestamps else None,
        "latest": max(timestamps).isoformat() if timestamps else None,
        "by_year": dict(Counter(dt.year for dt in timestamps)),
        "by_month": dict(Counter(f"{dt.year}-{dt.month:02d}" for dt in timestamps))
    } if timestamps else {"total_with_timestamps": 0}
    
    # Анализ текстовых полей
    text_samples = []
    empty_desc_count = 0
    for item in data[:10]:  # Выборка первых 10 записей
        name = item.get("name", "")
        desc = item.get("desc", "")
        if not desc.strip():
            empty_desc_count += 1
        text_samples.append({
            "list": item.get("list", ""),
            "name_length": len(name),
            "desc_length": len(desc),
            "has_desc": bool(desc.strip())
        })
    
    return {
        "record_count": len(data),
        "list_distribution": dict(list_distribution.most_common()),
        "time_stats": time_stats,
        "text_field_stats": {
            "empty_desc_ratio": f"{empty_desc_count}/{len(data)}",
            "sample_records": text_samples
        },
        "feature_candidates": [
            "list_category (nominal)",
            "name_text (string)",
            "timestamp_year (ordinal)",
            "timestamp_month (cyclic)"
        ]
    }

if __name__ == "__main__":
    result = analyze_trello_data()
    print(json.dumps(result, indent=2, ensure_ascii=False))
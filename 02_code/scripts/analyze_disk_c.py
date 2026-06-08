# analyze_disk_c.py
import os
import json
from pathlib import Path

def get_size(path):
    """Рекурсивный расчет размера директории"""
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            try:
                total += get_size(entry.path)
            except PermissionError:
                pass
    return total

def analyze_disk_c():
    results = []
    critical_paths = [
        "C:\\Windows\\Temp",
        "C:\\Users\\" + os.environ.get('USERNAME', 'User') + "\\Downloads",
        "C:\\Users\\" + os.environ.get('USERNAME', 'User') + "\\Desktop",
        "C:\\Users\\" + os.environ.get('USERNAME', 'User') + "\\AppData\\Local\\Temp",
        "C:\\$Recycle.Bin"
    ]
    
    for path in critical_paths:
        if os.path.exists(path):
            size_gb = get_size(path) / (1024**3)
            if size_gb > 0.1:  # Показываем только >100 МБ
                results.append({
                    "path": path,
                    "size_gb": round(size_gb, 2),
                    "safe_to_clean": True if "Temp" in path or "Downloads" in path else False
                })
    
    return results

if __name__ == "__main__":
    print("Анализ диска C: (только безопасные для проверки пути)")
    results = analyze_disk_c()
    
    if results:
        print("\nКандидаты на очистку:")
        for item in results:
            safe = "✅ БЕЗОПАСНО" if item["safe_to_clean"] else "⚠️ ТРЕБУЕТ ОСТОРОЖНОСТИ"
            print(f"  {item['path']}: {item['size_gb']} ГБ - {safe}")
    else:
        print("Крупных временных файлов не найдено")
    
    # Сохраняем отчет
    with open("C:\\disk_c_analysis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nОтчет сохранен: C:\\disk_c_analysis.json")

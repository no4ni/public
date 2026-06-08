import psutil
import json
from datetime import datetime
import sys

def collect_metrics():
    """Сбор системных метрик"""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
        "disk_percent": psutil.disk_usage('/').percent,
        "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
    }
    
    # Топ-3 процесса по памяти
    top_processes = []
    for proc in psutil.process_iter(['name', 'memory_percent', 'cpu_percent']):
        try:
            info = proc.info
            if info['memory_percent']:
                top_processes.append({
                    "name": info['name'],
                    "memory_percent": info['memory_percent'],
                    "cpu_percent": info['cpu_percent'] or 0
                })
        except:
            pass
    
    # Сортируем по памяти и берем топ-3
    top_processes.sort(key=lambda x: x['memory_percent'], reverse=True)
    metrics["top_processes"] = top_processes[:3]
    
    return metrics

if __name__ == "__main__":
    try:
        metrics = collect_metrics()
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f'{{"error": "{str(e)}"}}')

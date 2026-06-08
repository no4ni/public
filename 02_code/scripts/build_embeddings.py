import json
import numpy as np
from pathlib import Path
from sklearn.cluster import KMeans

def build_embeddings_and_clusters(root_path: str = r"E:\AGI") -> dict:
    """Построение эмбеддингов и кластеризация без внешних зависимостей (заглушка для совместимости)."""
    # Загрузка датасета
    dataset_path = Path(root_path) / "embedding_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    # Статистика по категориям
    category_counts = {}
    for item in dataset:
        cat = item["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Выделение записей категории "Распределить" для кластеризации
    redistribute_items = [item for item in dataset if item["category"] == "Распределить"]
    
    # Заглушка: эмуляция эмбеддингов (реальная реализация требует sentence-transformers)
    # Размерность 384 соответствует all-MiniLM-L6-v2
    np.random.seed(42)
    fake_embeddings = np.random.randn(len(dataset), 384).astype(np.float32)
    
    # Кластеризация только для категории "Распределить"
    redistribute_indices = [i for i, item in enumerate(dataset) if item["category"] == "Распределить"]
    if redistribute_indices and len(redistribute_indices) >= 5:
        k = min(8, len(redistribute_indices) // 5)  # Макс. 8 кластеров, мин. 5 записей на кластер
        kmeans = KMeans(n_clusters=k, random_state=0, n_init=10)
        cluster_labels = kmeans.fit_predict(fake_embeddings[redistribute_indices])
        
        # Привязка кластеров к записям
        cluster_assignments = {}
        for idx, label in zip(redistribute_indices, cluster_labels):
            cluster_assignments[dataset[idx]["id"]] = int(label)
    else:
        cluster_assignments = {}
    
    # Сохранение эмбеддингов (бинарный формат)
    embeddings_path = Path(root_path) / "embeddings.npy"
    np.save(embeddings_path, fake_embeddings)
    
    # Сохранение метаданных кластеров
    clusters_path = Path(root_path) / "clusters_redistribute.json"
    with open(clusters_path, "w", encoding="utf-8") as f:
        json.dump({
            "algorithm": "KMeans (simulated)",
            "n_clusters": len(set(cluster_assignments.values())) if cluster_assignments else 0,
            "assignments": cluster_assignments,
            "note": "Real embeddings require sentence-transformers installation"
        }, f, ensure_ascii=False, indent=2)
    
    return {
        "total_records": len(dataset),
        "category_distribution": category_counts,
        "redistribute_count": len(redistribute_items),
        "proposed_clusters": len(set(cluster_assignments.values())) if cluster_assignments else 0,
        "embeddings_saved": str(embeddings_path),
        "clusters_saved": str(clusters_path),
        "dependencies_required": [
            "sentence-transformers>=2.2.0",
            "torch>=1.6.0",
            "scikit-learn>=0.24.0"
        ]
    }

if __name__ == "__main__":
    result = build_embeddings_and_clusters()
    print(json.dumps(result, ensure_ascii=False, indent=2))
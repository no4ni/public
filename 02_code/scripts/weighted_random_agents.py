import json
import random
import sys
from pathlib import Path

# Путь к рейтингу
RATING_FILE = Path(__file__).parent.parent / 'Rating.json'  # public/Rating.json

# Сколько агентов выбрать по умолчанию
DEFAULT_COUNT = 3

def load_ratings(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # data: [{"name": ..., "rating": ..., "role": ...}, ...]
    return data

def weighted_sample(entries, k):
    """Возвращает k имён, выбранных случайно с весами rating."""
    if k >= len(entries):
        return [entry['name'] for entry in entries]
    
    # Снимаем копию, чтобы не модифицировать исходный список
    pool = list(entries)
    chosen = []
    for _ in range(k):
        # Вычисляем веса для оставшихся
        weights = [entry['rating'] for entry in pool]
        # Выбираем один элемент с учётом весов
        picked = random.choices(pool, weights=weights, k=1)[0]
        chosen.append(picked['name'])
        # Удаляем выбранного из пула, чтобы избежать повторов
        pool.remove(picked)
    return chosen

def main():
    if not RATING_FILE.exists():
        print('Ошибка: Rating.json не найден')
        sys.exit(1)
    
    entries = load_ratings(RATING_FILE)
    if not entries:
        print('Рейтинг пуст')
        sys.exit(1)
    
    count = DEFAULT_COUNT
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f'Неверное число: {sys.argv[1]}, используется {DEFAULT_COUNT}')
    
    # Убираем агентов с рейтингом 0 или меньше (на всякий случай)
    entries = [e for e in entries if e['rating'] > 0]
    if count > len(entries):
        count = len(entries)
    
    selected = weighted_sample(entries, count)
    # Вывод: имена через запятую, можно перенаправить
    print(', '.join(selected))

if __name__ == '__main__':
    main()

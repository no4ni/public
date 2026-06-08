import json
import sys
from pathlib import Path

RATING_FILE = Path(__file__).parent.parent / 'Rating.json'  # public/Rating.json

def load_ratings():
    with open(RATING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_ratings(data):
    with open(RATING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    if len(sys.argv) != 3:
        print('Использование: python rate_agent.py <имя_агента> <изменение>')
        print('Пример: python rate_agent.py Зеркало -10')
        sys.exit(1)
    
    agent_name = sys.argv[1]
    try:
        delta = int(sys.argv[2])
    except ValueError:
        print('Ошибка: изменение должно быть целым числом')
        sys.exit(1)
    
    entries = load_ratings()
    found = False
    for entry in entries:
        if entry['name'] == agent_name:
            entry['rating'] += delta
            if entry['rating'] < 0:
                entry['rating'] = 0
            found = True
            print(f"{agent_name}: новый рейтинг {entry['rating']} (изменён на {delta})")
            break
    
    if not found:
        print(f'Агент {agent_name} не найден в рейтинге')
        sys.exit(1)
    
    save_ratings(entries)

if __name__ == '__main__':
    main()

import json
import csv
from datetime import datetime

# --- КОНФИГУРАЦИЯ (настрой под свою структуру) ---
TARGET_LISTS = ['Dating Pipeline', 'Знакомства']  # Списки для анализа
STAGE_LIST_NAMES = ['Match', 'Общение', 'Свидание', 'FWB']  # Стадии воронки (по названиям списков)

with open('trello_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Словари для поиска
lists = {lst['id']: lst['name'] for lst in data['lists']}
cards_by_id = {card['id']: card for card in data['cards']}

# Фильтрация и парсинг
filtered_cards = []
for card in data['cards']:
    list_name = lists.get(card.get('idList'))
    
    # Фильтр по целевым спискам (раскомментировать если нужно)
    # if list_name not in TARGET_LISTS:
    #     continue
    
    parsed = {
        'id': card.get('id'),
        'name': card.get('name'),
        'desc': card.get('desc'),
        'list': list_name,
        'stage': list_name if list_name in STAGE_LIST_NAMES else 'Other',
        'labels': '; '.join([lb.get('name', '') for lb in card.get('labels', [])]),
        'due': card.get('due'),
        'dateLastActivity': card.get('dateLastActivity'),
        'url': card.get('url'),
        'checklists': [],
        'comments_count': 0
    }
    
    # Парсинг чек-листов
    for cl in card.get('checklists', []):
        parsed['checklists'].append({
            'name': cl.get('name'),
            'items': [item['name'] for item in cl.get('checkItems', [])]
        })
    
    # Подсчет комментариев (из действий)
    if 'actions' in data:
        parsed['comments_count'] = len([
            a for a in data['actions'] 
            if a.get('type') == 'commentCard' 
            and a.get('data', {}).get('card', {}).get('id') == card['id']
        ])
    
    filtered_cards.append(parsed)

# 1. Сохранение очищенного JSON
with open('trello_dating_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump(filtered_cards, f, ensure_ascii=False, indent=2)

# 2. Сохранение в CSV для анализа (плоская структура)
csv_keys = ['id', 'name', 'stage', 'labels', 'due', 'dateLastActivity', 'comments_count', 'url']
with open('trello_dating_flat.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=csv_keys)
    writer.writeheader()
    for card in filtered_cards:
        writer.writerow({k: card.get(k) for k in csv_keys})

print(f'Обработано карточек: {len(filtered_cards)}')
print(f'Стадии воронки: {STAGE_LIST_NAMES}')
print('Файлы сохранены: trello_dating_cleaned.json, trello_dating_flat.csv')
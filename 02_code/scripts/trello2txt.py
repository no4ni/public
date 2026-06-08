import json

with open('trello_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Словарь списков: id -> название
lists = {lst['id']: lst['name'] for lst in data['lists']}

# Парсим карточки
parsed_cards = []
for card in data['cards']:
    parsed = {
        'name': card.get('name'),
        'desc': card.get('desc'),
        'list': lists.get(card.get('idList')),
        'labels': [{'name': lb.get('name'), 'color': lb.get('color')} for lb in card.get('labels', [])],
        'due': card.get('due'),
        'dateLastActivity': card.get('dateLastActivity'),
        'url': card.get('url')
    }
    parsed_cards.append(parsed)

# Сохраняем очищенный JSON
with open('trello_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump(parsed_cards, f, ensure_ascii=False, indent=2)

print(f'Обработано карточек: {len(parsed_cards)}')
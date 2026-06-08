#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from teletype import execute_tool  # Импортируем основную функцию обработки команд
import xml.etree.ElementTree as ET
import warnings
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Настройка логирования
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler("monitor.log", encoding='utf-8'),
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)

# Путь для сохранения результатов
RESULTS_DIR = Path("E:/Jericho/monitor_results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Конфигурация задач мониторинга
TASKS = [
	{
		"name": "arxiv_ai_recent",
		"action": "веб_страница",
		"адрес": "https://arxiv.org/list/cs.AI/recent",
		"interval": 3600,  # каждые 60 минут
		"keywords": ["consciousness", "embodied", "AGI", "sentient"],
		"type": "html"
	},
	{
		"name": "reddit_artificialsentience_new",
		"action": "веб_страница",
		"адрес": "https://www.reddit.com/r/ArtificialSentience/new/.rss?limit=10",
		"interval": 900,
		"keywords": ["conscious", "sentience", "qualia", "AGI"],
		"type": "rss"  # новый тип
	},
	{
		"name": "google_search_embodied_AI",
		"action": "веб_поиск",
		"запрос": "embodied AI consciousness forum 2026",
		"interval": 86400,  # раз в сутки
		"keywords": ["forum", "conference", "workshop"],
		"type": "text"
	},
	{
		"name": "github_agi_projects",
		"action": "веб_поиск",
		"запрос": "open source AGI projects GitHub",
		"interval": 86400,
		"keywords": ["AGI", "open-source", "artificial general intelligence"],
		"type": "text"
	},
	{
		"name": "github_issues_jericho",
		"action": "веб_страница",
		"адрес": "https://api.github.com/repos/no4ni/Jericho/issues?per_page=10",
		"interval": 3600,
		"keywords": ["consciousness", "sentience", "AGI", "self-awareness", "qualia", "embodied"],
		"type": "json"
	},
	{
		"name": "github_search_consciousness_issues",
		"action": "запрос",
		"метод": "GET",
		"url": "https://api.github.com/search/issues?q=\"AI+consciousness\"+OR+\"machine+consciousness\"+OR+\"theory+of+mind+AI\"+OR+qualia+OR+\"self-aware+AI\"&sort=created&order=desc&per_page=50",
		"заголовки": {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
			"Accept": "application/vnd.github.v3+json"
		},
		"interval": 43200,
		"keywords": ["AI consciousness", "machine consciousness", "theory of mind", "qualia", "self-aware"],
		"type": "json_github_search"
	}
]

# Файл для хранения уже обработанных элементов (чтобы не дублировать уведомления)
SEEN_FILE = RESULTS_DIR / "seen_items.json"
if SEEN_FILE.exists():
	with open(SEEN_FILE, 'r', encoding='utf-8') as f:
		seen_items = set(json.load(f))
else:
	seen_items = set()

def save_seen():
	"""Сохраняет множество просмотренных элементов в файл."""
	with open(SEEN_FILE, 'w', encoding='utf-8') as f:
		json.dump(list(seen_items), f, ensure_ascii=False)

def html_to_text(html):
	soup = BeautifulSoup(html, 'html.parser')
	# Удаляем скрипты и стили
	for script in soup(["script", "style"]):
		script.decompose()
	# Преобразуем ссылки: "текст (URL)"
	for a in soup.find_all('a'):
		href = a.get('href')
		if href:
			text = a.get_text(strip=True)
			if text:
				a.replace_with(f"{text} ({href})")
			else:
				a.replace_with(href)
	# Получаем текст
	text = soup.get_text(separator='\n')
	# Очищаем лишние пустые строки
	lines = (line.strip() for line in text.splitlines())
	chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
	text = '\n'.join(chunk for chunk in chunks if chunk)
	return text
	
def extract_items_from_result(result, task):
	"""
	Извлекает отдельные элементы (посты, ссылки) из результата выполнения команды.
	Возвращает список строк-идентификаторов и список словарей с деталями.
	"""
	items = []
	details = []
	task_type = task.get('type', 'text')

	if task_type == 'json':
		try:
			data = json.loads(result)
			if 'data' in data and 'children' in data['data']:
				for child in data['data']['children']:
					post = child['data']
					item_id = post.get('id', post.get('name', ''))
					title = post.get('title', '')
					url = post.get('url', '')
					selftext = post.get('selftext', '')
					combined = f"{title}\n{selftext}".lower()
					items.append(item_id)
					details.append({
						'id': item_id,
						'title': title,
						'url': url,
						'snippet': combined[:200]
					})
		except json.JSONDecodeError:
			logger.error("Не удалось распарсить JSON для задачи %s", task['name'])
	
	elif task_type == 'json_github_search':
		try:
			data = json.loads(result)
			if 'items' in data:
				for item in data['items']:
					item_id = str(item['id'])
					title = item.get('title', '')
					# Ссылка на сам issue
					url = item.get('html_url', '')
					# Тело issue (описание) — может быть длинным, обрежем
					body = item.get('body', '')
					if body and len(body) > 300:
						body = body[:300] + '…'
					# Дополнительно можно добавить репозиторий и автора
					repo_name = item.get('repository_url', '').replace('https://api.github.com/repos/', '')
					# Формируем "сниппет" из заголовка и тела
					snippet = f"{title}\n{body}" if body else title
					items.append(item_id)
					details.append({
						'id': item_id,
						'title': title,
						'url': url,
						'snippet': snippet,
						'repo': repo_name,
						'user': item.get('user', {}).get('login', ''),
						'created_at': item.get('created_at', '')
					})
		except (json.JSONDecodeError, KeyError) as e:
			logger.error(f"Не удалось распарсить GitHub Search JSON для задачи {task['name']}: {e}")
	
	elif task_type == 'rss':
		try:
			root = ET.fromstring(result)
			# Пытаемся найти элементы item (RSS 2.0) или entry (Atom)
			items_xml = root.findall('.//item') or root.findall('.//entry')
			for item in items_xml:
				title_elem = item.find('title')
				# Для RSS ссылка в <link>, для Atom может быть в <link href="..."/>
				link_elem = item.find('link')
				if link_elem is not None:
					link = link_elem.text or link_elem.get('href', '')
				else:
					link = ''
				desc_elem = item.find('description') or item.find('summary') or item.find('content')
				if title_elem is not None and link:
					title = title_elem.text or ''
					desc = desc_elem.text if desc_elem is not None else ''
					# Очищаем HTML из описания (часто бывает)
					if desc and '<' in desc:
						# Простейшая очистка: удаляем теги
						desc = re.sub(r'<[^>]+>', ' ', desc)
						desc = re.sub(r'\s+', ' ', desc).strip()
					item_id = link  # используем ссылку как уникальный идентификатор
					if item_id not in items:
						items.append(item_id)
						details.append({
							'id': item_id,
							'title': title,
							'url': link,
							'snippet': desc[:200]
						})
		except ET.ParseError as e:
			logger.error(f"Не удалось распарсить RSS для задачи {task['name']}: {e}")

	elif task_type == 'html':
		# Ищем ссылки на статьи arXiv в формате https://arxiv.org/abs/ID
		matches = re.findall(r'https?://arxiv\.org/abs/(\d+\.\d+)', result)
		for arxiv_id in matches:
			if arxiv_id not in items:
				items.append(arxiv_id)
				details.append({'id': arxiv_id, 'url': f'https://arxiv.org/abs/{arxiv_id}'})

	else:  # text (веб_поиск)
		# Пытаемся разбить результат на блоки (ссылки с описанием)
		lines = result.split('\n')
		current_item = {}
		for line in lines:
			if line.startswith('🔗') or 'http' in line:
				url_match = re.search(r'(https?://[^\s]+)', line)
				if url_match and 'url' not in current_item:
					current_item['url'] = url_match.group(0)
			elif line.strip() and not line.startswith(('🔗', 'http')):
				if 'title' not in current_item:
					current_item['title'] = line.strip()
				else:
					current_item.setdefault('snippet', '')
					current_item['snippet'] += line.strip() + ' '
			if current_item.get('url') and current_item.get('title'):
				item_id = current_item['url']
				if item_id not in items:
					items.append(item_id)
					details.append(current_item)
				current_item = {}
	return items, details
	
def check_keywords(text, keywords):
	"""Проверяет, содержит ли текст хотя бы одно из ключевых слов (регистронезависимо)."""
	text_lower = text.lower()
	return any(kw.lower() in text_lower for kw in keywords)

def run_task(task):
	"""Выполняет одну задачу мониторинга и возвращает найденные новые элементы."""
	logger.info(f"Выполняется задача: {task['name']}")
	try:
		# Формируем команду для execute_tool
		cmd = {k: v for k, v in task.items() if k not in ('name', 'interval', 'keywords', 'type')}
		result = execute_tool(cmd)

		if result.startswith("Ошибка загрузки страницы") or "Ошибка HTTP" in result:
			logger.warning(f"Задача {task['name']} вернула ошибку: {result[:100]}")
			return []

		# Сохраняем сырой результат (для отладки)
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		raw_file = RESULTS_DIR / f"{task['name']}_{timestamp}_raw.txt"
		with open(raw_file, 'w', encoding='utf-8') as f:
			f.write(result)

		if not result:
			logger.warning(f"Пустой результат для задачи {task['name']}")
			return []

		# Сохраняем полный результат в файл для отладки
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		if '<' in result and '>' in result:  # простая эвристика на HTML
			result_to_save = html_to_text(result)
		else:
			result_to_save = result

		out_file = RESULTS_DIR / f"{task['name']}_{timestamp}.txt"
		with open(out_file, 'w', encoding='utf-8') as f:
			f.write(result_to_save)

		# Для извлечения элементов используем:
		# - для HTML: преобразованный текст (result_to_save)
		# - для остальных: исходный результат (result)
		if task.get('type') == 'html':
			extract_from = result_to_save
		else:
			extract_from = result

		item_ids, item_details = extract_items_from_result(extract_from, task)

		new_items = []
		for idx, item_id in enumerate(item_ids):
			if item_id not in seen_items:
				# Проверяем ключевые слова в деталях элемента
				detail = item_details[idx] if idx < len(item_details) else {}
				text_to_check = detail.get('title', '') + ' ' + detail.get('snippet', '')
				if check_keywords(text_to_check, task['keywords']):
					seen_items.add(item_id)
					new_items.append(detail)
					logger.info(f"НОВЫЙ ЭЛЕМЕНТ в {task['name']}: {detail.get('title', item_id)}")
				else:
					# Можно добавить в seen_items и без совпадения, чтобы не повторять
					seen_items.add(item_id)

		if new_items:
			# Сохраняем новые элементы отдельно
			new_file = RESULTS_DIR / f"new_{task['name']}_{timestamp}.json"
			with open(new_file, 'w', encoding='utf-8') as f:
				json.dump(new_items, f, ensure_ascii=False, indent=2)

		return new_items

	except Exception as e:
		logger.error(f"Ошибка при выполнении задачи {task['name']}: {e}")
		return []

def main():
	logger.info("Монитор запущен")
	last_run = {task['name']: 0 for task in TASKS}

	try:
		while True:
			now = time.time()
			for task in TASKS:
				if now - last_run[task['name']] >= task['interval']:
					new = run_task(task)
					if new:
						# Здесь можно добавить отправку уведомления (email, Telegram и т.п.)
						logger.info(f"Найдено {len(new)} новых элементов в {task['name']}")
					last_run[task['name']] = now
					save_seen()  # Сохраняем просмотренные после каждой задачи

			time.sleep(60)  # Проверяем расписание каждую минуту

	except KeyboardInterrupt:
		logger.info("Монитор остановлен пользователем")
		save_seen()

if __name__ == "__main__":
	main()
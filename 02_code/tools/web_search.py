# web_search.py — агрегатор поиска: DuckDuckGo + Tavily
import sys
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import io
import contextlib
import json
import argparse
from typing import List, Dict
from urllib.parse import urlparse

# Добавляем путь к ddgs_tool
ACTIONS_DIR = r"E:\vikhr-llama\agent\tools\actions"
if ACTIONS_DIR not in sys.path:
	sys.path.insert(0, ACTIONS_DIR)

try:
	from ddgs_tool.ddgs_tool import ddgs
except ImportError as e:
	print(f"[!] Не удалось импортировать модуль ddgs.ddgs_tool: {e}", file=sys.stderr)
	sys.exit(1)

def suppress_output(func, *args, **kwargs):
	"""Подавляет stdout/stderr при вызове функции."""
	with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
		return func(*args, **kwargs)

def fetch_ddgs(query: str, max_results: int = 10) -> List[Dict]:
	"""Получает результаты от DuckDuckGo через ddgs_tool."""
	try:
		raw = suppress_output(ddgs, query)
		return parse_ddgs_output(raw)
	except Exception as e:
		print(f"[!] Ошибка DuckDuckGo: {e}", file=sys.stderr)
		return []

import re

def clean_snippet(text: str) -> str:
    if not text:
        return "[Описание отсутствует]"
    # 1. Удаляем все изображения ![alt](url)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    # 2. Заменяем Markdown ссылки [текст](url) на "текст - url\n"
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 - \2\n', text)
    # 3. Удаляем оставшиеся пустые скобки и кавычки
    text = re.sub(r'\(\)|\[\]|"', '', text)
    # 4. Заменяем несколько подряд идущих точек (остатки от разделителей) на пробел
    text = re.sub(r'\.{2,}', ' ', text)
    # 5. Удаляем возможные последовательности " - \n - " и т.п.
    text = re.sub(r'\s*-\s*\n\s*-\s*', '\n', text)
    # 6. Сжимаем множественные пробелы и переводы строк
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    # 7. Убираем висящие тире и пробелы в начале/конце строк
    lines = [line.strip(' -') for line in text.split('\n') if line.strip()]
    # 8. Собираем обратно, убираем пустые строки
    cleaned = '\n'.join(lines)
    return cleaned or "[Описание отсутствует]"

def fetch_tavily(query: str, api_key: str, max_results: int = 10) -> List[Dict]:
	"""Получает результаты от Tavily API."""
	if not api_key:
		return []
	try:
		import requests
		resp = requests.post(
			"https://api.tavily.com/search",
			json={
				"api_key": api_key,
				"query": query,
				"max_results": max_results,
				"include_answer": False,
				"include_raw_content": False
			},
			timeout=15
		)
		data = resp.json()
		results = []
		for item in data.get("results", []):
			url = item.get("url")
			if not url:
				continue
			title = item.get("title", "") or url.split('/')[-1] or "Без названия"
			snippet = clean_snippet(item.get("content", ""))
			results.append({
				"url": url,
				"title": title,
				"snippet": snippet
			})
		return results
	except Exception as e:
		print(f"[!] Ошибка Tavily: {e}", file=sys.stderr)
		return []
		
def parse_ddgs_output(raw: str) -> List[Dict]:
	"""Парсит строку формата: Title\nBody\n🔗 URL\n\n..."""
	results = []
	blocks = raw.split('\n\n')
	for block in blocks:
		if not block.strip():
			continue
		lines = block.strip().split('\n')
		url = None
		url_idx = -1
		for i, line in enumerate(lines):
			if line.startswith('🔗 '):
				url = line[2:].strip()
				url_idx = i
				break
		if not url:
			continue
		if url_idx > 0:
			title = lines[0].strip()
			snippet = '\n'.join(lines[1:url_idx]).strip()
		else:
			title = ""
			snippet = ""
		results.append({
			"url": url,
			"title": title,
			"snippet": snippet
		})
	return results

def aggregate_results(results_lists: List[List[Dict]]) -> List[Dict]:
	"""Объединяет списки результатов, дедуплицирует по URL, выбирает лучший сниппет."""
	aggregated = {}
	for results in results_lists:
		for item in results:
			url = item.get("url")
			if not url:
				continue
			title = item.get("title", "")
			snippet = item.get("snippet", "")
			if url in aggregated:
				existing = aggregated[url]
				# Если новый сниппет длиннее или старый пуст, заменяем
				if len(snippet) > len(existing["snippet"]):
					existing["snippet"] = snippet
				# Заголовок тоже берём более длинный
				if len(title) > len(existing["title"]):
					existing["title"] = title
			else:
				aggregated[url] = {
					"url": url,
					"title": title,
					"snippet": snippet
				}
	return list(aggregated.values())

def main():
	parser = argparse.ArgumentParser(description="Агрегированный веб-поиск (DuckDuckGo + Tavily)")
	parser.add_argument("query", nargs="+", help="Поисковый запрос")
	parser.add_argument("--tavily-key", help="API ключ Tavily (если не указан, используется только DDG)")
	parser.add_argument("--max-results", type=int, default=10, help="Максимальное число результатов от каждого провайдера")
	args = parser.parse_args()

	query = " ".join(args.query)
	
	# 1. DuckDuckGo
	ddgs_results = fetch_ddgs(query, args.max_results)
	
	# 2. Tavily (если есть ключ)
	tavily_results = []
	if args.tavily_key:
		tavily_results = fetch_tavily(query, args.tavily_key, args.max_results)
	
	# 3. Агрегация
	all_results = aggregate_results([ddgs_results, tavily_results])
	
	# 4. Вывод в стандартном текстовом формате
	for item in all_results:
		print(item["title"])
		print(item["snippet"])
		print(f"🔗 {item['url']}")
		print()

if __name__ == "__main__":
	main()
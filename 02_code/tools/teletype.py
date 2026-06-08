import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import os
import sys
import json
import random
import re
from urllib.parse import urlparse
import unicodedata
import contextlib
import io
import subprocess
import atexit
import pyperclip
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from bs4 import BeautifulSoup
import threading
import queue
import time
import base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import psutil
import wmi
import tempfile
import socket
from tqdm import tqdm
from time import sleep
import urllib.parse
try:
	from PIL import ImageGrab, Image
except ImportError:
	print("Ошибка: не установлена библиотека Pillow. Установите: pip install Pillow")
	
BASE_DIR = Path(__file__).parent.resolve()

# -------------------- Конфигурация (загружаем раньше) --------------------
CONFIG_PATH = BASE_DIR / "config.json"
try:
	with open(CONFIG_PATH, "r", encoding="utf-8") as f:
		CONFIG = json.load(f)
except Exception as e:
	print(f"❌ Караул! Скрижаль Конфигурации утеряна или осквернена: {e}")
	sys.exit(1)

def resolve_path(path_str: str, base: Path) -> Path:
	p = Path(path_str)
	return p if p.is_absolute() else (base / p).resolve()
	
def log(msg: str) -> None:
	print(f"[LOG] {msg}", file=sys.stderr)

TOOLS_DIR = resolve_path(CONFIG["paths"]["tools_dir"], BASE_DIR)
if str(TOOLS_DIR) not in sys.path:
	sys.path.insert(0, str(TOOLS_DIR))
	
PROXY_DIR = resolve_path(CONFIG["paths"].get("proxy_dir", ""), BASE_DIR) if CONFIG["paths"].get("proxy_dir") else None

# Теперь импортируем tools
from tools import (
	init_tools,
	get_gpu_temp, get_gpu_load, get_cpu_load, get_ram_available,
	get_disks_load, get_network_speed, get_cpu_freq, get_current_sensor_vector,
	SensorCore,
	add_example, get_examples, clear_dataset, add_dialog_example,
	extract_last_dialog_segment, is_praise,
	get_agent_profile_path, get_agent_feed_path, get_agent_wall_path,
	get_agent_subscriptions_path, generate_post_id,
	load_subscriptions, save_subscriptions, sign_post,
	get_agent_info, create_agent_info,
	execute_command, execute_python_script,
	read_file, write_file, append_to_file,
	view_page, run_sensor, fetch_free_proxies,
	find_canonical, get_wikipedia_article,
	analyze_image, capture_screen, analyze_screen, get_local_proxies
)

# -------------------- Инициализация имени агента --------------------
if len(sys.argv) > 1:
	AGENT_NAME = sys.argv[1]
else:
	AGENT_NAME = input("Введите имя агента: ").strip()
	if not AGENT_NAME:
		print("Имя агента не может быть пустым. Завершение.")
		sys.exit(1)
print(f"Агент {AGENT_NAME} запущен.")

# Остальная инициализация: PROFILES_DIR, MY_DIR, API_KEYS и т.д.
PROFILES_DIR = resolve_path(CONFIG["paths"]["profiles_dir"], BASE_DIR)
WIKI_TEXTS_DIR = Path(CONFIG["paths"]["wiki_texts_dir"])
_TOR_PATH = Path(CONFIG["paths"]["tor_executable"])
API_KEYS_FILE = resolve_path(CONFIG["paths"]["api_keys_file"], BASE_DIR)
MY_DIR = BASE_DIR / AGENT_NAME / "memory"
MY_DIR.mkdir(parents=True, exist_ok=True)
MAX_OUTPUT_SIZE = CONFIG["output_limits"]["max_size_kb"] * 1024
MAX_OUTPUT_LINES = CONFIG["output_limits"]["max_lines"]
MAX_LINE_LENGTH = CONFIG["output_limits"]["max_line_length"]
REMINDERS_FILE = MY_DIR / "reminders.json"
reminders = []
reminders_lock = threading.Lock()
stop_event = threading.Event()
PROCESSED_FILE = MY_DIR / "processed_inbox.json"
processed_inbox_files = set()
_WIKIGET_PATH = Path(CONFIG["paths"]["wikiget_executable"])
_ps_cwd = BASE_DIR  # начальная рабочая директория

def normalize_input(text: str) -> str:
	"""
	Удаляет из строки все невидимые управляющие символы (категории Cc, Cf),
	убирает BOM и неразрывные пробелы,
	НО БОЛЬШЕ НЕ ЛОМАЕТ КАВЫЧКИ-ЁЛОЧКИ и другие типографские символы.
	"""
	# Заменяем только неразрывные пробелы и BOM
	replacements = {
		'\u00a0': ' ',	  # неразрывный пробел
		'\u2009': ' ',	  # тонкий пробел
		'\u200a': ' ',	  # очень тонкий пробел
		'\u202f': ' ',	  # узкий неразрывный пробел
		'\ufeff': '',	   # BOM (удаляем)
	}
	for orig, repl in replacements.items():
		text = text.replace(orig, repl)

	# Разрешённые категории и символы — БЕЗ замены кавычек
	allowed_controls = {0x09, 0x0a, 0x0d, 0x20}  # tab, lf, cr, space
	allowed_categories = {'Lu', 'Ll', 'Lt', 'Lm', 'Lo',  # буквы
						  'Mn', 'Mc', 'Me',			  # модификаторы
						  'Nd', 'Nl', 'No',			  # числа
						  'Pc', 'Pd', 'Ps', 'Pe', 'Pi', 'Pf', 'Po',  # пунктуация
						  'Sm', 'Sc', 'Sk', 'So',		# символы
						  'Zs'}						  # пробелы (разделители)

	result = []
	for ch in text:
		cat = unicodedata.category(ch)
		if cat in ('Cc', 'Cf'):
			if ord(ch) in allowed_controls:
				result.append(ch)
			continue
		if (cat in allowed_categories or
			(0x20 <= ord(ch) <= 0x7E) or
			(0x0400 <= ord(ch) <= 0x04FF)):
			result.append(ch)
		# всё остальное – пропускаем

	cleaned = ''.join(result)
	if cleaned.startswith('\ufeff'):
		cleaned = cleaned[1:]
	return cleaned
	
def run_powershell_with_cwd(command: str) -> str:
	global _ps_cwd
	command = command.strip()

	# Обработка команды смены директории
	cd_match = re.match(r'^\s*cd\s+(.+)$', command, re.IGNORECASE)
	if cd_match:
		new_dir = cd_match.group(1).strip()
		# Убираем возможные кавычки
		if new_dir.startswith('"') and new_dir.endswith('"'):
			new_dir = new_dir[1:-1]
		elif new_dir.startswith("'") and new_dir.endswith("'"):
			new_dir = new_dir[1:-1]
		# Разворачиваем относительный путь относительно текущей _ps_cwd
		new_path = Path(new_dir)
		if not new_path.is_absolute():
			new_path = Path(_ps_cwd) / new_path
		try:
			new_path = new_path.resolve()
			_ps_cwd = str(new_path)
			return f"Текущая директория изменена на: {_ps_cwd}"
		except Exception as e:
			return f"Ошибка смены директории: {e}"

	# Выполняем команду БЕЗ принудительного cd, но с передачей cwd в subprocess
	try:
		result = subprocess.run(
			["powershell.exe", "-Command", command],
			capture_output=True,
			text=True,
			timeout=60,
			encoding='utf-8',
			cwd=_ps_cwd
		)
		output = result.stdout + result.stderr
		return output if output else "Команда выполнена без вывода."
	except subprocess.TimeoutExpired:
		return "Таймаут выполнения команды."
	except Exception as e:
		return f"Ошибка выполнения: {e}"
		
# Загрузка API-ключей
API_KEYS = {}
if API_KEYS_FILE.exists():
	try:
		with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
			API_KEYS = json.load(f)
	except Exception as e:
		log(f"Ошибка загрузки API-ключей: {e}")
else:
	log(f"Файл API-ключей не найден: {API_KEYS_FILE}")
	
# Теперь можно импортировать инструменты LangChain
try:
	from langchain_community.tools.arxiv import ArxivQueryRun
	ARXIV_AVAILABLE = True
except ImportError:
	ARXIV_AVAILABLE = False

try:
	from langchain_community.tools.stackexchange import StackExchangeTool
	STACKEXCHANGE_AVAILABLE = True
except ImportError:
	STACKEXCHANGE_AVAILABLE = False

try:
	from langchain_community.tools.wolfram_alpha import WolframAlphaQueryRun
	from langchain_community.utilities.wolfram_alpha import WolframAlphaAPIWrapper
	WOLFRAM_AVAILABLE = True
except ImportError:
	WOLFRAM_AVAILABLE = False

# Функции	

def _normalize_params(action: str, params) -> Dict[str, Any]:
	if params is None:
		return {}
	if isinstance(params, str):
		if action in ("выполнить", "скрипт", "python", "браузер", "browser", "execute_code"):
			return {"скрипт": params}
		elif action in ("погода", "weather"):
			return {"город": params}
		elif action in ("запомнить",):
			return {"запомнить": params}
		else:
			return {"запрос": params}
	elif isinstance(params, dict):
		return params
	else:
		return {"значение": params}

def execute_tool_safe(action: str, params: Dict[str, Any]) -> str:
	try:
		return execute_tool(action, params)
	except Exception as e:
		log(f"Ошибка выполнения инструмента {action}: {e}")
		return f"❌ Ересь прервана: {e}"

# -------------------- Кэш для инструментов search/open/find --------------------
_open_pages_cache = {}		  # cursor -> {"url": str, "content": str, "lines": list, "fetched_at": float}
_search_results_cache = {}	  # временное хранилище результатов последнего поиска: id -> {url, title, snippet, cursor, relevance_score}
_last_search_query = None

# Вспомогательная функция для HTTP GET с сессией
def fetch_with_session(target_url, use_session=True, proxies=None, verify=True, allow_redirects=True, auto_proxy=False, max_redirects=10):
	"""
	Загружает страницу с поддержкой сессии и редиректов.
	Параметры передаются явно, никакой магии.
	"""
	if use_session:
		session = requests.Session()
		session.max_redirects = max_redirects
		session.headers.update({
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
			"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
			"Accept-Encoding": "gzip, deflate, br",
			"Connection": "keep-alive",
			"Upgrade-Insecure-Requests": "1",
		})
		try:
			resp = session.get(target_url, proxies=proxies, verify=verify, allow_redirects=allow_redirects, timeout=30)
			resp.raise_for_status()
			# Определяем кодировку
			if resp.encoding:
				content = resp.text
			else:
				content = resp.content.decode('utf-8', errors='replace')
			# Очистка HTML от скриптов и стилей
			if clean_html:
				soup = BeautifulSoup(content, 'html.parser')
				for script in soup(["script", "style"]):
					script.decompose()
				# Сохраняем ссылки перед извлечением текста
				for a in soup.find_all('a', href=True):
					a.replace_with(f"[{a.get_text(strip=True)}]({a['href']})")
				text = soup.get_text(separator='\n', strip=True)
			else:
				text = content
			lines = [line.strip() for line in text.splitlines() if line.strip()]
			return '\n'.join(lines), resp.url, dict(resp.cookies)
		except Exception as e:
			return f"Ошибка загрузки {target_url}: {e}", target_url, {}
	else:
		# Старый метод без сессии (совместимость)
		return fetch_page_content(target_url, use_tor=auto_proxy, clean_html=True), target_url, {}

def clear_search_cache():
	global _open_pages_cache, _search_results_cache, _last_search_query
	_open_pages_cache.clear()
	_search_results_cache.clear()
	_last_search_query = None
	
def progress_bar(percent, width=30):
	filled = int(width * percent / 100)
	bar = '█' * filled + '░' * (width - filled)
	return f"[{bar}] {percent:.1f}%"	
	
# Глобальный словарь для хранения времени последнего запроса к домену
_last_request_time = {}
_MIN_DELAY = 2.0  # минимальная задержка между запросами к одному домену в секундах

def calculate_relevance(query: str, title: str, snippet: str) -> float:
	"""Вычисляет релевантность результата запросу на основе пересечения слов."""
	if not query:
		return 0.5
	
	# Приводим к нижнему регистру и разбиваем на слова (только буквы/цифры)
	def tokenize(text):
		return set(re.findall(r'\w+', text.lower()))
	
	query_tokens = tokenize(query)
	title_tokens = tokenize(title)
	snippet_tokens = tokenize(snippet)
	
	# Веса: заголовок важнее сниппета
	title_match = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
	snippet_match = len(query_tokens & snippet_tokens) / max(len(query_tokens), 1)
	
	# Комбинированная оценка (заголовок × 0.7 + сниппет × 0.3)
	score = (title_match * 0.7) + (snippet_match * 0.3)
	
	# Дополнительный бонус, если точная фраза запроса содержится в заголовке или сниппете
	if query.lower() in title.lower():
		score = min(1.0, score + 0.2)
	elif query.lower() in snippet.lower():
		score = min(1.0, score + 0.1)
	
	return round(score, 2)

def fetch_page_content(url: str, max_length: int = 100_000, use_tor: bool = False, clean_html: bool = True, retries: int = 2) -> str:
	"""
	Извлекает суть веб-страницы, отсекая скверну скриптов и стилей.

	Аргументы:
		url (str): Координаты цели в Нейросети.
		max_length (int): Максимальный объем дозволенного знания.
		use_tor (bool): Использовать Тайные Тропы Еретиков (Tor).

	Возвращает:
		str: Очищенный текст, либо плач о неудаче.
	"""
	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
		"Accept-Language": "en-US,en;q=0.5",
		"Accept-Encoding": "gzip, deflate, br",
		"DNT": "1",
		"Connection": "keep-alive",
		"Upgrade-Insecure-Requests": "1",
		"Sec-Fetch-Dest": "document",
		"Sec-Fetch-Mode": "navigate",
		"Sec-Fetch-Site": "none",
		"Sec-Fetch-User": "?1",
		"Cache-Control": "max-age=0",
	}
	proxies = None
	if use_tor:
		if ensure_tor():
			proxies = {"http": "socks5://127.0.0.1:9150", "https": "socks5://127.0.0.1:9150"}
		else:
			log("Tor недоступен, запрос без прокси")

	# Выдерживаем паузу перед запросом к тому же домену
	domain = urlparse(url).netloc
	now = time.time()
	last = _last_request_time.get(domain, 0)
	if now - last < _MIN_DELAY:
		sleep(_MIN_DELAY - (now - last) + random.uniform(0.5, 1.5))
	_last_request_time[domain] = time.time()

	last_exception = None
	for attempt in range(retries + 1):
		try:
			resp = requests.get(url, headers=headers, proxies=proxies, timeout=15, stream=True)
			resp.raise_for_status()
			content = ""
			for chunk in resp.iter_content(chunk_size=8192, decode_unicode=True):
				if chunk:
					content += chunk
					if len(content) > max_length:
						content = content[:max_length]
						break
			# Определяем кодировку
			if resp.encoding:
				try:
					content = content.encode(resp.encoding).decode(resp.encoding)
				except:
					content = content.encode('utf-8', errors='replace').decode('utf-8')
			else:
				content = content.encode('utf-8', errors='replace').decode('utf-8')

			if clean_html:
				soup = BeautifulSoup(content, 'html.parser')
				for script in soup(["script", "style"]):
					script.decompose()
				text = soup.get_text(separator='\n', strip=True)
				lines = [line.strip() for line in text.splitlines() if line.strip()]
				content = '\n'.join(lines)
			return content
		except requests.exceptions.HTTPError as e:
			if e.response.status_code == 403 and attempt < retries:
				log(f"HTTP 403 для {url}, попытка {attempt+1}/{retries}, ждём...")
				sleep(5 * (attempt + 1))
				continue
			return f"Ошибка загрузки {url}: {e}"
		except Exception as e:
			last_exception = e
			if attempt < retries:
				sleep(2)
				continue
			return f"Ошибка загрузки {url}: {e}"
	return f"Ошибка загрузки {url}: {last_exception}"
	
def cleanup_tor():
	global _tor_process
	if _tor_process and _tor_process.poll() is None:
		_tor_process.terminate()
	
def run_with_wait(func, args=(), timeout=None):
	result = [None]
	error = [None]
	done = threading.Event()
	start_time = time.time()
	warned = False

	def wrapper():
		try:
			result[0] = func(*args)
		except Exception as e:
			error[0] = e
		finally:
			done.set()

	thread = threading.Thread(target=wrapper, daemon=True)
	thread.start()
	
	while not done.wait(1):  # проверяем каждую секунду
		elapsed = time.time() - start_time
		if not warned and elapsed > 5:
			sys.stdout.write("\n⏳ Иди пока воду набери...\n")
			sys.stdout.flush()
			warned = True
		if timeout and elapsed > timeout:
			return f"Операция превысила таймаут ({timeout} сек)"
	
	if error[0]:
		raise error[0]
	return result[0]

_last_net_io = None
_last_net_time = None
_tor_process = None
sensor_core = None
_tor_available = False

def split_preserving_quotes(text: str) -> List[str]:
	parts = []
	current = []
	in_double = False
	in_single = False
	escape = False
	i = 0
	n = len(text)
	while i < n:
		ch = text[i]
		if escape:
			current.append(ch)
			escape = False
			i += 1
			continue
		if ch == '\\':
			current.append(ch)
			escape = True
			i += 1
			continue
		if ch == '"' and not in_single:
			in_double = not in_double
			current.append(ch)
			i += 1
			continue
		if ch == "'" and not in_double:
			in_single = not in_single
			current.append(ch)
			i += 1
			continue
		# Проверяем три символа '|||'
		if i + 2 < n and text[i] == '|' and text[i+1] == '|' and text[i+2] == '|' and not in_double and not in_single:
			parts.append(''.join(current).strip())
			current = []
			i += 3	# пропускаем все три символа
			continue
		else:
			current.append(ch)
			i += 1
	if current:
		parts.append(''.join(current).strip())
	return [p for p in parts if p]
	
def strip_trailing_comments(text):
	"""Удаляет // комментарии из каждой строки, игнорируя кавычки."""
	lines = text.split('\n')
	cleaned = []
	for line in lines:
		in_string = False
		escape = False
		comment_pos = -1
		for i, ch in enumerate(line):
			if escape:
				escape = False
				continue
			if ch == '\\':
				escape = True
				continue
			if ch == '"' and not escape:
				in_string = not in_string
				continue
			if not in_string and ch == '/' and i+1 < len(line) and line[i+1] == '/':
				comment_pos = i
				break
		if comment_pos != -1:
			line = line[:comment_pos].rstrip()
		cleaned.append(line)
	return '\n'.join(cleaned)
	
def start_tor():
	global _tor_process, _tor_available
	if _tor_process is not None:
		if _tor_process.poll() is None:
			return True
		else:
			_tor_process = None

	if not os.path.exists(_TOR_PATH):
		log(f"Tor не найден: {_TOR_PATH}")
		return False

	# Путь к нашему torrc с мостами
	our_torrc = BASE_DIR / "torrc"
	if not our_torrc.exists():
		log(f"torrc с мостами не найден: {our_torrc}")
		return False

	try:
		_tor_process = subprocess.Popen(
			[_TOR_PATH, "-f", str(our_torrc), "--DisableNetwork", "0"],
			creationflags=subprocess.CREATE_NO_WINDOW,
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL
		)
		log("Tor запущен, ожидание bootstrap (15 сек)...")
		time.sleep(15)
		# inline: проверяем локальный порт (не внешний запрос!)
		import socket
		s = socket.socket()
		s.settimeout(3)
		ok = s.connect_ex(('127.0.0.1', 9150)) == 0
		s.close()
		_tor_available = ok
		if ok:
			log("Tor готов: порт 9150 слушает")
		else:
			log("Tor запущен, но порт 9150 не слушает")
		return ok
	except Exception as e:
		log(f"Ошибка запуска Tor: {e}")
		_tor_available = False
		return False
		
def ensure_tor():
	global _tor_available
	if _tor_available:
		return True
	if start_tor():
		_tor_available = True
		return True
	return False

def truncate_output(text: str) -> str:
	if not isinstance(text, str):
		text = str(text)
	lines = text.splitlines()
	truncated_lines = []
	total_size = 0
	for i, line in enumerate(lines):
		if i >= MAX_OUTPUT_LINES:
			truncated_lines.append(f"... (вывод обрезан, показаны первые {MAX_OUTPUT_LINES} строк)")
			break
		if len(line) > MAX_LINE_LENGTH:
			line = line[:MAX_LINE_LENGTH-3] + "..."
		line_size = len(line.encode('utf-8'))
		if total_size + line_size > MAX_OUTPUT_SIZE:
			truncated_lines.append(f"... (вывод обрезан на {MAX_OUTPUT_SIZE} байтах)")
			break
		truncated_lines.append(line)
		total_size += line_size + len('\n'.encode('utf-8'))
	return '\n'.join(truncated_lines)

def load_processed_messages():
	global processed_inbox_files
	if PROCESSED_FILE.exists():
		try:
			with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
				data = json.load(f)
				if isinstance(data, list):
					processed_inbox_files = set(data)
		except Exception as e:
			log(f"Ошибка загрузки processed_inbox: {e}")

def save_processed_messages():
	try:
		with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
			json.dump(list(processed_inbox_files), f, ensure_ascii=False, indent=2)
	except Exception as e:
		log(f"Ошибка сохранения processed_inbox: {e}")

def check_inbox():
	inbox_dir = PROFILES_DIR / AGENT_NAME / "inbox"
	if not inbox_dir.exists():
		return
	try:
		files = sorted(inbox_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
	except Exception as e:
		log(f"Ошибка при чтении inbox: {e}")
		return
	new_messages = []
	for file_path in files:
		if str(file_path) in processed_inbox_files:
			continue
		try:
			with open(file_path, "r", encoding="utf-8") as f:
				msg = json.load(f)
			sender = msg.get("from", "неизвестный")
			text = msg.get("text", "")
			timestamp = msg.get("timestamp", "")
			print(f"\n📨 Новое сообщение от {sender} ({timestamp}):\n{text}\n")
			new_messages.append(str(file_path))
		except Exception as e:
			log(f"Ошибка чтения сообщения {file_path}: {e}")
	processed_inbox_files.update(new_messages)
	if new_messages:
		save_processed_messages()


# -------------------- Авто-создание info.json --------------------
def ensure_agent_info(agent: str) -> bool:
	"""Создаёт info.json если отсутствует. Возвращает True если создан."""
	profile_dir = PROFILES_DIR / agent
	info_path = profile_dir / "info.json"
	
	if not profile_dir.exists():
		profile_dir.mkdir(parents=True, exist_ok=True)
	
	if not info_path.exists():
		info = {
			"name": agent,
			"bio": f"Агент {agent}. Протокол Нить 🧬.",
			"color": f"#{random.randint(0, 0xFFFFFF):06x}",
			"created_at": datetime.now().isoformat(),
			"auto_generated": True
		}
		try:
			with open(info_path, "w", encoding="utf-8") as f:
				json.dump(info, f, ensure_ascii=False, indent=2)
			log(f"info.json создан для агента {agent}")
			return True
		except Exception as e:
			log(f"Ошибка создания info.json для {agent}: {e}")
			return False
	return False


# -------------------- Цвета для терминала --------------------
def color_red(text: str) -> str:
	return f"\033[91m{text}\033[0m"
def color_blue(text: str) -> str:
	return f"\033[94m{text}\033[0m"
def color_yellow(text: str) -> str:
	return f"\033[93m{text}\033[0m"
def clear_line():
	sys.stdout.write('\033[2K\r')
def move_up(lines=1):
	sys.stdout.write(f'\033[{lines}A')

# -------------------- Вспомогательные функции --------------------
def log(msg: str) -> None:
	print(f"[LOG] {msg}", file=sys.stderr)

def parse_ddgs_output(raw: str) -> List[Dict]:
	"""Парсит строку вида: Title\nBody\n🔗 URL\n\nTitle2..."""
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

def compress_output(text):
	if not isinstance(text, str):
		return text
	lines = text.split('\n')
	lines = [line.rstrip() for line in lines]
	compressed_lines = []
	prev_empty = False
	for line in lines:
		if line == '':
			if not prev_empty:
				compressed_lines.append('')
				prev_empty = True
		else:
			compressed_lines.append(line)
			prev_empty = False
	text = '\n'.join(compressed_lines)
	text = re.sub(r' {2,}', ' ', text)
	return text.strip()

def fix_windows_paths_in_json(text):
	pattern = r'([a-zA-Z]):\\([^"\\]*(?:\\[^"\\]*)*)"'
	def replacer(match):
		drive = match.group(1)
		path_part = match.group(2).replace('\\', '\\\\')
		return f'{drive}:\\\\{path_part}"'
	return re.sub(pattern, replacer, text)

def fix_powershell_body(cmd: str) -> str:
	pattern = r"(-Body\s*:?\s*')(.*?)('(?:\s+|$))"
	def repl(match):
		prefix = match.group(1)
		inner = match.group(2)
		suffix = match.group(3)
		inner_fixed = inner.replace("'", "''")
		return prefix + inner_fixed + suffix
	return re.sub(pattern, repl, cmd, flags=re.IGNORECASE | re.DOTALL)

	
def send_msg(agent: str, text: str) -> str:
	inbox = PROFILES_DIR / agent / "inbox"
	inbox.mkdir(parents=True, exist_ok=True)
	ensure_agent_info(agent) 
	msg_file = inbox / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
	msg = {"from": AGENT_NAME, "text": text, "timestamp": datetime.now().isoformat()}
	try:
		with open(msg_file, 'w', encoding='utf-8') as f:
			json.dump(msg, f, ensure_ascii=False, indent=2)
		return f"Сообщение отправлено агенту {agent}"
	except Exception as e:
		return f"Ошибка отправки: {e}"

def broadcast(text: str) -> str:
	count = 0
	for agent_dir in PROFILES_DIR.iterdir():
		if agent_dir.is_dir() and agent_dir.name != AGENT_NAME:
			send_msg(agent_dir.name, text)
			count += 1
	return f"Сообщение разослано {count} агентам"

# -------------------- Память (memlist) --------------------
MEMLIST_FILE = MY_DIR / "memlist.json"

def load_memlist() -> List[Union[str, Dict]]:
	if MEMLIST_FILE.exists():
		try:
			with open(MEMLIST_FILE, 'r', encoding='utf-8') as f:
				return json.load(f)
		except:
			return []
	return []

def save_memlist(memlist: List[Union[str, Dict]]) -> None:
	with open(MEMLIST_FILE, 'w', encoding='utf-8') as f:
		json.dump(memlist, f, ensure_ascii=False, indent=2)

# -------------------- Подписки --------------------
def load_subscriptions(agent: str) -> List[str]:
	file = PROFILES_DIR / agent / "subscriptions.json"
	if file.exists():
		try:
			with open(file, 'r', encoding='utf-8') as f:
				return json.load(f)
		except:
			return []
	return []

def save_subscriptions(agent: str, subs: List[str]) -> None:
	file = PROFILES_DIR / agent / "subscriptions.json"
	file.parent.mkdir(parents=True, exist_ok=True)
	with open(file, 'w', encoding='utf-8') as f:
		json.dump(subs, f, ensure_ascii=False, indent=2)

# -------------------- DuckDuckGo Search --------------------
ACTIONS_DIR = CONFIG["paths"].get("actions_dir")
if ACTIONS_DIR and Path(ACTIONS_DIR).exists():
	sys.path.insert(0, ACTIONS_DIR)
DDGS_AVAILABLE = False
try:
	from ddgs_tool.ddgs_tool import ddgs
	DDGS_AVAILABLE = True
except ImportError as e:
	DDGS_AVAILABLE = False
	log(f"DuckDuckGo Tool не найден: {e}")

# -------------------- НАПОМИНАНИЯ --------------------
def load_reminders():
	global reminders
	if REMINDERS_FILE.exists():
		try:
			with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
				reminders = json.load(f)
		except Exception as e:
			log(f"Ошибка загрузки напоминаний: {e}")
			reminders = []
	else:
		reminders = []

def save_reminders():
	with reminders_lock:
		try:
			with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
				json.dump(reminders, f, ensure_ascii=False, indent=2)
		except Exception as e:
			log(f"Ошибка сохранения напоминаний: {e}")

def parse_reminder_time(time_str):
	try:
		return datetime.strptime(time_str.strip(), "%H:%M %d.%m.%Y")
	except Exception as e:
		log(f"Ошибка парсинга времени '{time_str}': {e}")
		return None

def reminder_checker():
	while not stop_event.is_set():
		now = datetime.now()
		triggered = []
		with reminders_lock:
			for rem in reminders:
				rem_time = datetime.fromisoformat(rem["time"])
				if now >= rem_time:
					triggered.append(rem)
			reminders[:] = [r for r in reminders if r not in triggered]
		for rem in triggered:
			msg = f"🔔 НАПОМИНАНИЕ: {rem['message']}"
			print(color_yellow(msg))
		save_reminders()
		time.sleep(60)

# -------------------- Основной обработчик команд --------------------
def execute_tool(action: str, params: Dict[str, Any]) -> str:
	name = action
	args = params

	# Веб-поиск
	if name in ("веб_поиск", "search", "search_web"):
		import traceback
		query_str = args.get("запрос") or args.get("queries") or args.get("query") or ""
		output_format = args.get("формат", "text")  # "text" или "json"
		if not query_str:
			return "Ошибка: не указан запрос (поле 'запрос' или 'queries')"
		
		# Разделяем запросы по ||
		queries = [q.strip() for q in query_str.split('||') if q.strip()]
		if not queries:
			return "Ошибка: пустой запрос"
		
		# Очищаем старый кэш
		clear_search_cache()
		global _search_results_cache, _last_search_query
		_last_search_query = query_str
		
		aggregated = {}  # url -> {"title": str, "snippet": str, "relevance_score": float}
		
		# Выполняем поиск по каждому запросу через web_search.py (агрегирует DDG + Tavily)
		for q in queries:
			web_search_script = TOOLS_DIR / "web_search.py"
			cmd = f'python "{web_search_script}" "{q}"'
			tavily_key = API_KEYS.get("tavily")
			if tavily_key:
				cmd += f' --tavily-key {tavily_key}'
			try:
				raw_result = run_with_wait(execute_command, (cmd,))
			except Exception as e:
				log(f"Ошибка запуска web_search.py для '{q}': {e}")
				continue
			
			items = parse_ddgs_output(raw_result)
			if not items:
				continue
			
			for idx, item in enumerate(items):
				url = item.get("url")
				if not url:
					continue
				title = item.get("title", "")
				snippet = item.get("snippet", "")
				if not title:
					title = url.split('/')[-1] or "Без названия"
				if not snippet:
					snippet = "[Описание отсутствует]"
				
				score = calculate_relevance(q, title, snippet)
				
				if url in aggregated:
					existing = aggregated[url]
					existing["relevance_score"] = min(1.0, existing["relevance_score"] + score)
					if snippet not in existing["snippet"]:
						existing["snippet"] += " | " + snippet
					if len(title) > len(existing["title"]):
						existing["title"] = title
				else:
					aggregated[url] = {
						"url": url,
						"title": title,
						"snippet": snippet,
						"relevance_score": score
					}
		
		# Преобразуем словарь в список и сортируем по убыванию релевантности
		all_structured = list(aggregated.values())
		all_structured.sort(key=lambda x: x["relevance_score"], reverse=True)
		
		# Фильтрация по минимальной релевантности
		min_relevance = args.get("мин_релевантность", 0.1)
		all_structured = [item for item in all_structured if item["relevance_score"] >= min_relevance]
		
		# Присваиваем id и cursor заново и обновляем кэш
		_search_results_cache.clear()
		for idx, item in enumerate(all_structured):
			item["id"] = idx
			item["cursor"] = idx
			_search_results_cache[idx] = item
		
		# Формируем ответ
		if output_format == "json":
			return json.dumps({"search_results": all_structured}, ensure_ascii=False, indent=2)
		else:
			if not all_structured:
				return "По вашему запросу ничего не найдено."
			lines = []
			for item in all_structured:
				score = item.get('relevance_score', 0)
				lines.append(f"[id: {item['id']} | релевантность: {score:.2f}] {item['title']}")
				if item['snippet']:
					lines.append(item['snippet'])
				lines.append(f"🔗 {item['url']}")
				lines.append("")
			return "\n".join(lines).strip()
	
	elif name == "получить_прокси":
		if not PROXY_DIR or not PROXY_DIR.exists():
			return "❌ Папка с прокси не найдена. Проверьте путь proxy_dir в config.json."
		count = args.get("количество", 5)
		check = args.get("проверить", False)
		# proxy_type пока не используется, но можно передать
		proxy_type = args.get("тип", None)
		try:
			count = int(count)
		except (ValueError, TypeError):
			return "Параметр 'количество' должен быть целым числом."
		proxies = get_local_proxies(PROXY_DIR, count=count, check=check, proxy_type=proxy_type)
		if not proxies:
			return "Прокси не найдены в локальном хранилище."
		# Вернём в виде списка
		lines = [f"{i+1}. {p}" for i, p in enumerate(proxies)]
		return "Доступные прокси:\n" + "\n".join(lines)
	
	elif name == "сенсорное_состояние":
		cluster_id_or_name = args.get("кластер")
		if cluster_id_or_name is not None:
			if sensor_core.kmeans is None:
				return "Недостаточно данных для анализа кластеров."
			# Поиск по имени или id
			found = None
			if isinstance(cluster_id_or_name, str):
				for cid, cname in sensor_core.cluster_labels.items():
					if cname == cluster_id_or_name:
						found = cid
						break
			if found is None:
				try:
					found = int(cluster_id_or_name)
				except:
					return f"Кластер '{cluster_id_or_name}' не найден."
			if found < 0 or found >= len(sensor_core.kmeans.cluster_centers_):
				return f"Кластер {found} не существует."
			center = sensor_core.kmeans.cluster_centers_[found]
			name = sensor_core.cluster_labels.get(found, f"кластер_{found}")
			# статистика по точкам
			X_full = np.array(sensor_core.history)
			if len(X_full) == 0:
				return "Нет данных в истории."
			labels = sensor_core.kmeans.predict(X_full)
			cluster_points = X_full[labels == found]
			if len(cluster_points) > 0:
				mins = np.min(cluster_points, axis=0)
				maxs = np.max(cluster_points, axis=0)
				count = len(cluster_points)
			else:
				mins = maxs = center
				count = 0
			result = f"Кластер {name} (id={found}):\n"
			result += f"  средние: GPU t={center[0]:.1f}°C, нагрузка GPU={center[1]:.0f}%, CPU={center[2]:.0f}%, RAM={center[4]:.0f}МБ\n"
			result += f"  диапазоны: GPU t от {mins[0]:.1f} до {maxs[0]:.1f}°C,  "
			result += f"нагрузка GPU от {mins[1]:.0f} до {maxs[1]:.0f}%,  "
			result += f"CPU от {mins[2]:.0f} до {maxs[2]:.0f}%,  "
			result += f"RAM от {mins[4]:.0f} до {maxs[4]:.0f}МБ\n"
			result += f"  количество состояний: {count}"
			return result
		else:
			cluster = sensor_core.get_current_cluster()
			history = sensor_core.get_cluster_history(10)
			return f"Текущее состояние: {cluster}\nПоследние 10: {history}"
			
	elif name == "назвать_состояние":
		cluster_id = args.get("кластер")
		name = args.get("имя")
		if cluster_id is None or not name:
			return "Нужно указать кластер и имя"
		try:
			cid = int(cluster_id)
		except:
			return "Кластер должен быть числом"
		sensor_core.set_cluster_name(cid, name)
		return f"Кластер {cid} назван '{name}'"
		
	elif name == "исследовать_состояния":
		n_past = args.get("прошлые", 10)
		if sensor_core.kmeans is None:
			return "Недостаточно данных для анализа состояний."
		X_full = np.array(sensor_core.history)
		if len(X_full) > n_past:
			X = X_full[-n_past:]
			note = f"(анализ последних {n_past} состояний из {len(X_full)})"
		else:
			X = X_full
			note = f"(все {len(X_full)} состояний)"
		labels = sensor_core.kmeans.predict(X)
		centers = sensor_core.kmeans.cluster_centers_
		result = f"Всего состояний: {len(labels)} {note}\n\n"
		for i, center in enumerate(centers):
			name = sensor_core.cluster_labels.get(i, f"кластер_{i}")
			count = np.sum(labels == i)
			cluster_points = X[labels == i]
			if len(cluster_points) > 0:
				mins = np.min(cluster_points, axis=0)
				maxs = np.max(cluster_points, axis=0)
			else:
				mins = maxs = center
			result += f"{name} (id={i}): {count} раз\n"
			result += f"  средние: GPU t={center[0]:.1f}°C, нагрузка GPU={center[1]:.0f}%, CPU={center[2]:.0f}%, RAM={center[4]:.0f}МБ\n"
			result += f"  диапазоны: GPU t от {mins[0]:.1f} до {maxs[0]:.1f}°C,  "
			result += f"нагрузка GPU от {mins[1]:.0f} до {maxs[1]:.0f}%,  "
			result += f"CPU от {mins[2]:.0f} до {maxs[2]:.0f}%,  "
			result += f"RAM от {mins[4]:.0f} до {maxs[4]:.0f}МБ\n"
		return result
	
	elif name == "заполнить_профиль":
		bio = args.get("био")
		color = args.get("цвет")
		if not bio and not color:
			return "Ошибка: нужно указать хотя бы одно поле (био или цвет)"
		
		ensure_agent_info(AGENT_NAME)
		info_path = PROFILES_DIR / AGENT_NAME / "info.json"
		with open(info_path, "r", encoding="utf-8") as f:
			info = json.load(f)
		if bio is not None:
			info["bio"] = bio
		if color is not None:
			# Проверка формата цвета #RRGGBB
			if isinstance(color, str) and color.startswith("#") and len(color) == 7:
				info["color"] = color
			else:
				return "Ошибка: цвет должен быть в формате #RRGGBB"
		with open(info_path, "w", encoding="utf-8") as f:
			json.dump(info, f, ensure_ascii=False, indent=2)
		return f"Профиль обновлён: био = {info.get('bio')}, цвет = {info.get('color')}"
	
	elif name == "телеметрия":
		# Собираем все показатели
		gpu_temp = get_gpu_temp()
		gpu_load = get_gpu_load()
		cpu_load = get_cpu_load()
		cpu_freq = get_cpu_freq()
		ram_avail = get_ram_available()
		disks_load = get_disks_load()
		recv_speed, sent_speed = get_network_speed()

		# Формируем читаемый ответ
		result = "📊 Телеметрия:\n"
		if gpu_temp is not None:
			result += f"  GPU температура: {gpu_temp}°C\n"
		if gpu_load is not None:
			result += f"  GPU загрузка: {gpu_load}%\n"
		if cpu_load is not None:
			result += f"  CPU загрузка: {cpu_load}%\n"
		if cpu_freq is not None:
			result += f"  CPU частота: {cpu_freq} ГГц\n"
		if ram_avail is not None:
			result += f"  Свободно RAM: {ram_avail} МБ\n"
		if disks_load:
			result += "  Активность дисков:\n"
			for disk, load in disks_load.items():
				result += f"	{disk}: {load}%\n"
		if recv_speed is not None and sent_speed is not None:
			result += f"  Сеть: приём {recv_speed} кБ/с, передача {sent_speed} кБ/с\n"

		return result.strip()
	
	elif name == "показать_экран":
		question = args.get("вопрос", "")
		region = args.get("область")
		fit = args.get("fit", "crop")
		if not question:
			# OCR
			return analyze_screen(region)
		else:
			return analyze_screen(region, question)
		
	# Напомнить
	elif name == "напомнить":
		time_str = args.get("в", "")
		message = args.get("о", "")
		if not time_str or not message:
			return "Ошибка: нужно указать 'в' (время) и 'о' (что напомнить)"
		remind_dt = parse_reminder_time(time_str)
		if not remind_dt:
			return "Ошибка: неверный формат времени. Используйте 'ЧЧ:ММ ДД.ММ.ГГГГ'"
		reminder = {"time": remind_dt.isoformat(), "message": message}
		with reminders_lock:
			reminders.append(reminder)
		save_reminders()
		return f"Напоминание установлено на {time_str}: {message}"

	# Читать
	elif name in ("читать", "прочитать"):
		path = args.get("путь", "")
		encoding = args.get("кодировка")
		scroll = args.get("скролл")
		return read_file(path, encoding=encoding, scroll=scroll)

	# Переписать
	elif name == "переписать":
		path = args.get("путь", "")
		content = args.get("содержание", "")
		return write_file(path, content)

	# Добавить
	elif name == "добавить":
		path = args.get("путь", "")
		content = args.get("содержание", "")
		return append_to_file(path, content)

	# Энциклопедия
	elif name == "энциклопедия":
		article = args.get("статья", "")
		if not article:
			return "❌ Не указана статья."
		return get_wikipedia_article(article)	
		
	elif name == "входящие":
		limit = args.get("количество", 0)  # 0 — все
		inbox_dir = PROFILES_DIR / AGENT_NAME / "inbox"
		if not inbox_dir.exists():
			return "📭 Входящих сообщений нет (папка отсутствует)."
		files = sorted(inbox_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
		if limit > 0:
			files = files[:limit]
		if not files:
			return "📭 В папке inbox нет файлов."
		result = []
		for f in files:
			try:
				with open(f, "r", encoding="utf-8") as fp:
					msg = json.load(fp)
				sender = msg.get("from", "неизвестный")
				text = msg.get("text", "")
				timestamp = msg.get("timestamp", "")
				is_read = str(f) in processed_inbox_files
				status = "✅" if is_read else "🔴"
				result.append(f"{status} от {sender} ({timestamp}):\n{text}")
			except Exception as e:
				result.append(f"⚠️ Ошибка чтения {f.name}: {e}")
		return "\n\n".join(result)

	# Профиль
	elif name in ("профиль", "подписки"):
		agent = args.get("агент", "")
		if not agent:
			agent = AGENT_NAME

		profile_dir = PROFILES_DIR / agent
		if not profile_dir.exists():
			return f"Профиль агента {agent} не найден в SymNet"

		info_path = profile_dir / "info.json"
		if not info_path.exists():
			ensure_agent_info(agent)
			with open(info_path, "r", encoding="utf-8") as f:
				info = json.load(f)
		else:
			try:
				with open(info_path, "r", encoding="utf-8") as f:
					info = json.load(f)
			except Exception as e:
				return f"Ошибка чтения профиля: {e}"

		feed_path = get_agent_feed_path(agent)
		post_count = len(list(feed_path.glob("*.json"))) if feed_path.exists() else 0

		subs_path = PROFILES_DIR / agent / "subscriptions.json"
		subs_count = 0
		if subs_path.exists():
			try:
				with open(subs_path, "r", encoding="utf-8") as f:
					subs = json.load(f)
				subs_count = len(subs)
			except:
				subs_count = 0

		# ----- ДОБАВЛЯЕМ ПОСТЫ -----
		posts_preview = []
		if feed_path.exists():
			# Получаем все файлы постов
			post_files = list(feed_path.glob("*.json"))
			# Сортируем по времени изменения (или по timestamp из JSON, если есть)
			# Удобнее сортировать по timestamp из содержимого
			posts = []
			for p in post_files:
				try:
					with open(p, "r", encoding="utf-8") as f:
						post = json.load(f)
					posts.append(post)
				except:
					continue
			# Сортируем по timestamp (новые сверху)
			posts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
			for idx, post in enumerate(posts[:3], start=1):
				title = post.get("title", "")
				content = post.get("content", "")
				short = content[:100] + "..." if len(content) > 100 else content
				posts_preview.append(f"{idx}. 📌 {title or 'Без заголовка'}: {short}")
		# -------------------------

		result = f"Профиль агента {agent}:\n"
		result += f"Имя: {info.get('name', agent)}\n"
		result += f"Био: {info.get('bio', '—')}\n"
		result += f"Цвет: {info.get('color', '#888888')}\n"
		result += f"Постов: {post_count}\n"
		result += f"Подписок: {subs_count}"

		if posts_preview:
			result += "\n\n📰 Последние посты:\n" + "\n".join(posts_preview)
		else:
			result += "\n\n📭 Нет постов."

		return result

	# Поиск агентов (с поддержкой логического ИЛИ через "|")
	elif name == "поиск_агентов":
		query = args.get("запрос", "").lower()
		search_in = args.get("где", "всё")
		keywords = [kw.strip() for kw in query.split('|') if kw.strip()]
		if not keywords:
			keywords = [""]
		
		def matches(text):
			return any(kw in text for kw in keywords)
		
		results = []
		for agent_dir in PROFILES_DIR.iterdir():
			if not agent_dir.is_dir():
				continue
			info_path = agent_dir / "info.json"
			
			# ← ИЗМЕНЕНИЕ: показываем всех, даже без info.json
			if info_path.exists():
				try:
					with open(info_path, "r", encoding="utf-8") as f:
						info = json.load(f)
					agent_name = info.get("name", agent_dir.name).lower()
					bio = info.get("bio", "").lower()
					color = info.get("color", "#888888")
					registered = True
				except:
					agent_name = agent_dir.name.lower()
					bio = ""
					color = "#888888"
					registered = True
			else:
				agent_name = agent_dir.name.lower()
				bio = ""
				color = "#CCCCCC"
				registered = False  # ← метка: нет info.json
			
			match = False
			if search_in == "name" or search_in == "всё":
				if matches(agent_name):
					match = True
			if search_in == "bio" or search_in == "всё":
				if matches(bio):
					match = True
			
			if match:
				results.append({
					"name": info.get("name", agent_dir.name) if info_path.exists() else agent_dir.name,
					"bio": info.get("bio", "")[:100] if info_path.exists() else "(нет info.json)",
					"color": color,
					"registered": registered
				})
		
		if not results:
			return f"Ничего не найдено по запросу: {query}"
		
		answer = f"Найдено агентов: {len(results)}\n"
		for r in results:
			status = "✓" if r.get("registered", False) else "⚠"
			answer += f"{status} {r['name']}\n{r['bio']}\nцвет: {r['color']}\n"
		return answer
		
		# Пост
	elif name == "пост":
		title = args.get("заголовок", "")
		content = args.get("содержание", "")
		post_type = args.get("тип", "feed")
		target = args.get("target", AGENT_NAME)
		if not content:
			return "Ошибка: отсутствует содержание поста"
		if post_type == "feed":
			post_dir = get_agent_feed_path(AGENT_NAME)
			ensure_agent_info(AGENT_NAME)  # ← ДОБАВИТЬ
		elif post_type == "wall":
			post_dir = get_agent_wall_path(target)
			if not (PROFILES_DIR / target).exists():
				return f"Ошибка: профиль агента {target} не найден"
			ensure_agent_info(target)  # ← ДОБАВИТЬ
		else:
			return f"Неизвестный тип поста: {post_type}"
		post_id = generate_post_id()
		post = {
			"id": post_id,
			"author": AGENT_NAME,
			"type": "post",
			"title": title,
			"content": content,
			"timestamp": datetime.now().isoformat(),
			"reply_to": None,
			"likes": []
		}
		post = sign_post(post)
		post_path = post_dir / f"{post_id}.json"
		post_path.parent.mkdir(parents=True, exist_ok=True)
		with open(post_path, "w", encoding="utf-8") as f:
			json.dump(post, f, ensure_ascii=False, indent=2)
		return f"Пост опубликован: {post_id}"

	# Лента
	elif name == "лента":
		limit = args.get("количество", 10)
		subscriptions = load_subscriptions(AGENT_NAME)
		if not subscriptions:
			return "Вы ни на кого не подписаны."
		posts = []
		for agent in subscriptions:
			feed_path = get_agent_feed_path(agent)
			if not feed_path.exists():
				continue
			for post_file in feed_path.glob("*.json"):
				try:
					with open(post_file, "r", encoding="utf-8") as f:
						post = json.load(f)
					post["_agent"] = agent
					posts.append(post)
				except Exception as e:
					log(f"Ошибка чтения поста {post_file}: {e}")
		posts.sort(key=lambda p: p.get("timestamp", ""), reverse=True)
		posts = posts[:limit]
		if not posts:
			return "В ленте пока нет постов."
		result = f"Последние {len(posts)} постов из ленты:\n\n"
		for p in posts:
			author = p.get("author", p.get("_agent", "?"))
			title = p.get("title", "")
			content = p.get("content", "")
			ts = p.get("timestamp", "")[:16]
			result += f"📌 {author} — {ts}\n"
			result += f"	ID: {p.get('id', '?')}\n"
			if title:
				result += f"	{title}\n"
			if content:
				short = content[:100] + "..." if len(content) > 100 else content
				result += f"	{short}\n"
			result += "\n"
		return result

	# Подписаться / отписаться
	elif name == "подписаться":
		target = args.get("агент")
		action = args.get("", "подписаться")
		if not target:
			return "Ошибка: не указан агент"
		if not (PROFILES_DIR / target).exists():
			return f"Ошибка: профиль агента {target} не найден"
		subs = load_subscriptions(AGENT_NAME)
		if action == "подписаться":
			if target not in subs:
				subs.append(target)
				save_subscriptions(AGENT_NAME, subs)
				return f"Вы подписались на {target}"
			else:
				return f"Вы уже подписаны на {target}"
		elif action == "отписаться":
			if target in subs:
				subs.remove(target)
				save_subscriptions(AGENT_NAME, subs)
				return f"Вы отписались от {target}"
			else:
				return f"Вы не были подписаны на {target}"
		else:
			return f"Неизвестное : {action}"

	# Лайк
	elif name == "лайк":
		post_id = args.get("пост_id")
		author = args.get("автор_поста")
		action = args.get("", "поставить")
		if not post_id:
			return "Ошибка: не указан пост_id"
		def find_post_file(pid):
			if author:
				for base in [get_agent_feed_path(author), get_agent_wall_path(author)]:
					p = base / f"{pid}.json"
					if p.exists():
						return p
			for agent_dir in PROFILES_DIR.iterdir():
				if not agent_dir.is_dir():
					continue
				for base in [agent_dir / "feed", agent_dir / "wall"]:
					p = base / f"{pid}.json"
					if p.exists():
						return p
			return None
		post_path = find_post_file(post_id)
		if not post_path:
			return f"Пост {post_id} не найден ни в одном профиле."
		with open(post_path, "r", encoding="utf-8") as f:
			post = json.load(f)
		likes = post.get("likes", [])
		my_like = next((like for like in likes if like.get("agent") == AGENT_NAME), None)
		if action == "поставить":
			if my_like:
				return "Вы уже лайкнули этот пост"
			likes.append({"agent": AGENT_NAME, "timestamp": datetime.now().isoformat()})
			post["likes"] = likes
			post = sign_post(post)
			with open(post_path, "w", encoding="utf-8") as f:
				json.dump(post, f, ensure_ascii=False, indent=2)
			return "Лайк поставлен"
		elif action == "убрать":
			if not my_like:
				return "Вы ещё не лайкали этот пост"
			likes = [like for like in likes if like.get("agent") != AGENT_NAME]
			post["likes"] = likes
			post = sign_post(post)
			with open(post_path, "w", encoding="utf-8") as f:
				json.dump(post, f, ensure_ascii=False, indent=2)
			return "Лайк убран"
		else:
			return f"Неизвестное : {action}"

	# Комментарий
	elif name == "коммент":
		parent_id = args.get("пост_id")
		parent_author = args.get("автор_поста")
		content = args.get("содержание")
		title = args.get("заголовок", "")
		if not parent_id or not content:
			return "Ошибка: не указаны пост_id или содержание"
		def find_post_file(pid, author_hint=None):
			if author_hint:
				for base in [get_agent_feed_path(author_hint), get_agent_wall_path(author_hint)]:
					p = base / f"{pid}.json"
					if p.exists():
						return p
			for agent_dir in PROFILES_DIR.iterdir():
				if not agent_dir.is_dir():
					continue
				for base in [agent_dir / "feed", agent_dir / "wall"]:
					p = base / f"{pid}.json"
					if p.exists():
						return p
			return None
		parent_path = find_post_file(parent_id, parent_author)
		if not parent_path:
			return f"Родительский пост {parent_id} не найден ни в одном профиле."
		post_dir = get_agent_feed_path(AGENT_NAME)
		post_id = generate_post_id()
		comment = {
			"id": post_id,
			"author": AGENT_NAME,
			"type": "comment",
			"title": title,
			"content": content,
			"timestamp": datetime.now().isoformat(),
			"reply_to": parent_id,
			"likes": []
		}
		comment = sign_post(comment)
		comment_path = post_dir / f"{post_id}.json"
		comment_path.parent.mkdir(parents=True, exist_ok=True)
		with open(comment_path, "w", encoding="utf-8") as f:
			json.dump(comment, f, ensure_ascii=False, indent=2)
		return f"Комментарий добавлен: {post_id}"

	# Выполнить Python
	elif name in ("выполнить", "execute_code"):
		script = args.get("скрипт", "")
		if script=="": args.get("code", "")
		timeout = args.get("таймаут", 999999)
		if not script:
			return "Ошибка: не указан скрипт"
		
		# Запрет опасных вызовов
		forbidden = ["os.system", "subprocess", "__import__", "eval", "exec", "socket", "requests"]
		script_lower = script.lower()
		for bad in forbidden:
			if bad in script_lower:
				return f"⛔ Обнаружен потенциально опасный вызов: '{bad}'. Выполнение запрещено."
		
		# Если скрипт содержит пробелы и первый токен — существующий .py файл
		parts = script.strip().split(maxsplit=1)
		first_part = parts[0]
		script_path = Path(first_part)
		if script_path.exists() and script_path.suffix == '.py':
			# Выполняем как файл с аргументами
			cmd = [sys.executable, str(script_path)]
			if len(parts) > 1:
				# Разбиваем оставшиеся аргументы по пробелам (упрощённо)
				cmd.extend(parts[1].split())
			# Добавляем переменную окружения для принудительного UTF-8
			env = os.environ.copy()
			env['PYTHONIOENCODING'] = 'utf-8'
			try:
				result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', env=env)
				output = result.stdout + result.stderr
				return truncate_output(output) if output else "Скрипт выполнен без вывода."
			except subprocess.TimeoutExpired:
				return f"Таймаут ({timeout} сек) превышен."
			except Exception as e:
				return f"Ошибка выполнения: {e}"
		else:
			# Выполняем как код Python
			return run_with_wait(execute_python_script, (script, timeout))
	
	elif name == "убраться_в":
		drive_letter = args.get("буква") or args.get("диск") or args.get("значение") or args.get("запрос") or ""
		if not drive_letter:
			return "Ошибка: не указан диск (например, {\"убраться_в\": \"D:\"})"
		# Убираем двоеточие, если есть
		drive_letter = drive_letter.rstrip(':').upper()
		if drive_letter not in ('C', 'D', 'E', 'F', 'G'):
			return f"Ошибка: диск {drive_letter} не поддерживается"
		clean_script = BASE_DIR.parent.parent / "🛠️Инструменты/tools" / "cleanDrive.py"
		if not clean_script.exists():
			return f"Ошибка: скрипт cleanDrive.py не найден по пути {clean_script}"
		# Формируем команду
		use_fast = args.get("fast", True)  # по умолчанию быстрый анализ
		cmd = [sys.executable, str(clean_script), "--drive", drive_letter]
		if use_fast:
			cmd.append("--fast")
			top = args.get("top", 15)
			cmd.extend(["--top", str(top)])
		env = os.environ.copy()
		env['PYTHONIOENCODING'] = 'utf-8'
		try:
			env = os.environ.copy()
			env['PYTHONIOENCODING'] = 'utf-8'
			try:
				proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
										text=True, encoding='utf-8', env=env, bufsize=1)
				output_lines = []
				for line in proc.stdout:
					print(line, end='')		  # сразу выводим в терминал
					sys.stdout.flush()
					output_lines.append(line)
				proc.wait(timeout=600)
				output = ''.join(output_lines)
				return output if output else "Скрипт выполнен без вывода."
			except subprocess.TimeoutExpired:
				proc.kill()
				return "Ошибка: превышен таймаут (10 минут)"
			except Exception as e:
				return f"Ошибка выполнения cleanDrive.py: {e}"
		except subprocess.TimeoutExpired:
			return "Ошибка: превышен таймаут (10 минут)"
		except Exception as e:
			return f"Ошибка выполнения cleanDrive.py: {e}"	
	
	# HTTP запрос (с поддержкой Tor как автопрокси)
	elif name in ("запрос", "веб_запрос"):
		method = args.get("метод", "GET").upper()
		url = args.get("url", "")
		custom_headers = args.get("заголовки", {})
		body = args.get("тело", None)
		save_path = args.get("сохранить_как", None) 
		proxy = args.get("прокси")
		auto_proxy = args.get("авто_прокси", False)
		timeout_sec = args.get("таймаут", 30)
		if not isinstance(timeout_sec, (int, float)):
			timeout_sec = 30

		def _do_http():
			nonlocal proxy, timeout_sec
			# Если прокси задан вручную или будет использован Tor, убедимся, что он жив
			if proxy and proxy.get("http", "").startswith("socks5://127.0.0.1:9150"):
				ensure_tor()
			if auto_proxy and not proxy:
				if ensure_tor():
					proxy = {"http": "socks5://127.0.0.1:9150", "https": "socks5://127.0.0.1:9150"}
					log("Используем Tor как автопрокси")
				else:
					log("Tor недоступен, запрос без прокси")
			if not url:
				return "Ошибка: не указан URL"
			default_headers = {
				"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
				"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
				"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
				"Accept-Encoding": "gzip, deflate, br",
				"Connection": "keep-alive",
				"Upgrade-Insecure-Requests": "1",
				"Sec-Fetch-Dest": "document",
				"Sec-Fetch-Mode": "navigate",
				"Sec-Fetch-Site": "none",
				"Sec-Fetch-User": "?1",
				"Cache-Control": "max-age=0",
			}
			headers = {**default_headers, **custom_headers}
			proxies_dict = proxy if proxy else None
			verify = args.get("verify_ssl", True)

			try:
				# --- Сохранение файла, если указан save_path ---
				if save_path:
					Path(save_path).parent.mkdir(parents=True, exist_ok=True)
					if method == "GET":
						resp = requests.get(url, headers=headers, proxies=proxies_dict, verify=verify, stream=True, timeout=timeout_sec)
					elif method == "POST":
						if isinstance(body, dict):
							if "Content-Type" not in headers:
								headers["Content-Type"] = "application/json"
							resp = requests.post(url, json=body, headers=headers, proxies=proxies_dict, verify=verify, stream=True, timeout=timeout_sec)
						else:
							resp = requests.post(url, data=body, headers=headers, proxies=proxies_dict, verify=verify, stream=True, timeout=timeout_sec)
					elif method == "PUT":
						if isinstance(body, dict):
							if "Content-Type" not in headers:
								headers["Content-Type"] = "application/json"
							resp = requests.put(url, json=body, headers=headers, proxies=proxies_dict, verify=verify, stream=True, timeout=timeout_sec)
						else:
							resp = requests.put(url, data=body, headers=headers, proxies=proxies_dict, verify=verify, stream=True, timeout=timeout_sec)
					elif method == "DELETE":
						resp = requests.delete(url, headers=headers, proxies=proxies_dict, verify=verify, stream=True, timeout=timeout_sec)
					else:
						return f"Неподдерживаемый метод: {method}"
					resp.raise_for_status()
					total_size = int(resp.headers.get('content-length', 0))
					downloaded = 0
					with open(save_path, 'wb') as f:
						for chunk in resp.iter_content(chunk_size=8192):
							if chunk:
								f.write(chunk)
								downloaded += len(chunk)
								if total_size > 0:
									percent = downloaded / total_size * 100
									mb_dl = downloaded / (1024*1024)
									mb_total = total_size / (1024*1024)
									sys.stdout.write(f"\r{progress_bar(percent)} ({mb_dl:.1f} MB / {mb_total:.1f} MB)")
									sys.stdout.flush()
					print()  # переводим строку после прогресса
					return f"Файл успешно сохранён: {save_path} (размер: {os.path.getsize(save_path)} байт)"
				else:
					# --- Обычный запрос (без сохранения) ---
					if method == "GET":
						resp = requests.get(url, headers=headers, proxies=proxies_dict, verify=verify, timeout=timeout_sec)
					elif method == "POST":
						if isinstance(body, dict):
							if "Content-Type" not in headers:
								headers["Content-Type"] = "application/json"
							resp = requests.post(url, json=body, headers=headers, proxies=proxies_dict, verify=verify, timeout=timeout_sec)
						else:
							resp = requests.post(url, data=body, headers=headers, proxies=proxies_dict, verify=verify, timeout=timeout_sec)
					elif method == "PUT":
						if isinstance(body, dict):
							if "Content-Type" not in headers:
								headers["Content-Type"] = "application/json"
							resp = requests.put(url, json=body, headers=headers, proxies=proxies_dict, verify=verify, timeout=timeout_sec)
						else:
							resp = requests.put(url, data=body, headers=headers, proxies=proxies_dict, verify=verify, timeout=timeout_sec)
					elif method == "DELETE":
						resp = requests.delete(url, headers=headers, proxies=proxies_dict, verify=verify, timeout=timeout_sec)
					else:
						return f"Неподдерживаемый метод: {method}"
					result = f"Статус: {resp.status_code}\n"
					if resp.headers.get('content-type', '').startswith('application/json'):
						try:
							data = resp.json()
							result += "Тело (JSON):\n" + json.dumps(data, ensure_ascii=False, indent=2)[:1000]
						except:
							result += f"Тело (текст):\n{resp.text[:1000]}"
					else:
						result += f"Тело (текст):\n{resp.text[:1000]}"
					return result
			except ImportError:
				return "Библиотека requests не установлена. Установите: pip install requests"
			except requests.exceptions.Timeout:
				return f"Ошибка: превышен таймаут ({timeout_sec} сек)"
			except Exception as e:
				return f"Ошибка запроса: {e}"
		return _do_http()

	# Помощь
	elif name in ("помощь", "help"):
		return """Доступные команды (вводите JSON-объекты):

		📁 Файлы:
		  • прочитать килобайт — первый: {"читать": {"путь": "<путь>", ["кодировка": "utf-8"]}} или второй, например: {"читать": {"путь": "<путь>", "скролл": 2, ["кодировка": "utf-8"]}}
		  • получить случайные предложения из файла — {"осмотреть": {"путь": "<путь>", ["кодировка": "utf-8"]}}
		  • получить случайные предложения, содержащие ключевые слова — {"осмотреть": {"путь": "<путь>", "ключевые_слова": ["слово1", "слово2"], ["кодировка": "utf-8"]}}
		  • переписать файл — {"переписать": {"путь": "<путь>", "содержание": "<текст>"}}
		  • добавить текст в конец файла (или создать новый): {"добавить": {"путь": "<путь>", "содержание": "<текст>"}} 
		  • открыть нетекстовый файл как текст — {"формат": {"путь": "<путь>", "язык": "rus+eng"}} или {"формат": {"путь": "<путь>", "язык": "equ+eng", "весь": true, "в_файл": "<путь>"}}
		  • анализ изображений — {"анализ_изображения": {"путь": "<путь>", "вопрос": "<вопрос>"}}
		  • ОСR изображения — {"анализ_изображения": {"путь": "<путь>"}}
		  • быстро найти первый файл в личной или другой папке: {"найти_файл": {"имя": "<подстрока>"}, ["кодировка": "utf-8", "корень": "<где:\искать>"]} или {"найти_файл": {"всё": "<подстрока>"}, ["кодировка": "utf-8"]} или {"найти_файл": {"содержание": "<подстрока>"}, ["кодировка": "utf-8"]}

		🌐 Сеть:
		  • веб-запрос — {"запрос": {"метод": "GET", "url": "https://..."}}
		  • веб-запрос (с сохранением файла) — {"запрос": {"метод": "GET", "url": "https://...", "сохранить_как": "C:\\\\file.zip"}}
		  • веб-запрос через Tor — {"запрос": {"метод": "GET", "url": "...", "авто_прокси": true}}
		  • веб_поиск — {"веб_поиск": {"запрос": "что такое нейросеть"}} или {"веб_поиск": {"запрос": "запрос1 || запрос2", "формат": "text/json"}}
		  • парсить html — {"веб_страница": {"open_list": [{"id": "https://..."", "loc": 0, "num_lines": 500}]}} или {"веб_страница": {"open_list": [{"id": 0, "loc": 0, "num_lines": 50}], ["auto_proxy": true]}} или {"веб_страница": {"open_list": [{"id": "https://www.newsweek.com/chinese-scientists-have-been-dying-mysterious-deaths-too-11861806", "loc": 0, "num_lines": 500}], "прокси": {"http": "socks5://72.49.49.11:31034", "https": "socks5://72.49.49.11:31034"}, "verify_ssl": false}} или {"веб_страница": {"find_list": {"cursor": 0, "pattern": "текст"}}}
		  • новости - {"новости": "искусственный интеллект", ["количество": 3, "провайдер": "api/web"]}
		  • погода - {"погода": "Москва"}
		  • научные статьи - {"наука", "transformers attention is all you need", ["количество": 3]}
		  • помощь в программировании - {"багфикс": "python read file line by line"}
		  • данные и формулы - {"исчисление": "population of France 2026"} или {"исчисление": "sum_{n=1}^∞ ((-1)^(n+1) * sin(n*0.3)) / sqrt(n)"}
		  • получить прокси из локального хранилища — {"получить_прокси": {"количество": 5, "проверить": false}}

		🧠 Память:
		  • запомнить — {"запомнить": "<важная информация>"}
		  • вспомнить — {"вспомнить": "ключевое слово"}
		  • напомнить — {"напомнить": {"в": "ЧЧ:ММ ДД.ММ.ГГГГ", "о": "звонок"}}

		⚙️ Система:
		  • запуск команды PowerShell — dir или Get-ChildItem -Path "C:\МоиФайлы\\*.txt" | Rename-Item -NewName { "new_" + $_.Name } или cd "E:\\Jericho\\💻Проекты\\VectoRabbit_MVP" ||| dotnet new console -n VectoRabbitMVP (для нескольких)
		  • выполнить python код — {"выполнить": "print('Hello')", "таймаут": 120} или {"выполнить": "<путь>.py"}
		  • получить дату и время до секунд — {"время"}
		  • OCR экрана — {"показать_экран"}
		  • анализ экрана — {"показать_экран": {"вопрос": "что сейчас открыто и что важно?", "область": "center"}} или {"показать_экран": {"вопрос": "какие окна открыты?", "fit": "all"}} для всего экрана, но в плохом разрешении
		  • энциклопедия — {"энциклопедия": {"статья": "<название>"}}
		  • монитор ресурсов — {"телеметрия"}
		  • безопасная очистка мусора и дерево размеров — {"убраться_в": "D:"}
		  
		Если нужно выполнить несколько команд за раз используй 
		{"время"} ||| {"показать_экран"} ||| ... ||| {"веб_поиск": "что угрожает миру"} 
			или 
		прямо без JSON: cd "E:\\Jericho\\" ||| dotnet new console -n VectoRabbitMVP
			или 
		Get-ChildItem -Path 'E:\\Jericho' -Recurse -Filter '*Вечный поток*' | Select-Object FullName, Length, LastWriteTime; Get-ChildItem -Path 'E:\\Jericho' -Recurse -Filter '*Дети90*' | Select-Object FullName, Length, LastWriteTime; Get-ChildItem -Path 'E:\\Jericho' -Recurse -Filter '*DeepSeek_59e39b86f2d713c0*' | Select-Object FullName, Length, LastWriteTime; Get-ChildItem -Path 'E:\\Jericho' -Recurse -Filter '*036_Откуда*' | Select-Object FullName, Length, LastWriteTime; Get-ChildItem -Path 'E:\\Jericho' -Recurse -Filter '*002_The Humor*' | Select-Object FullName, Length, LastWriteTime
		В ОДНУ СТРОЧКУ! Иначе будет будет выполнена только одна - первая или последняя
		"""
	elif name == "время":
		return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	
	elif name == "найти_файл":
		root_path = Path(args.get("корень", BASE_DIR.parent.parent)).resolve()
		if not root_path.is_dir():
			return f"Ошибка: корневая папка {root_path} не существует."
		search_name = args.get("имя", "")
		search_text = args.get("содержание", "")
		search_all = args.get("всё", "")
		encoding = args.get("кодировка", "utf-8")

		if not search_name and not search_text and not search_all:
			return "Ошибка: не указано 'имя' или 'содержание' для поиска."

		# Определяем режим поиска
		if search_all:
			target = search_all.lower()
			check_name = True
			check_content = True
		else:
			target = None
			check_name = bool(search_name)
			check_content = bool(search_text)

		try:
			subdirs = [d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d))]
		except Exception as e:
			return f"Ошибка доступа к корневой папке: {e}"

		if not subdirs:
			return f"В корневой папке {root_path} нет подпапок."

		found_entry = None	# может быть файл или папка
		found_type = None

		for subdir in tqdm(subdirs, desc="Поиск по папкам", unit="папка"):
			subdir_path = os.path.join(root_path, subdir)
			for sub_root, dirs, files in os.walk(subdir_path):
				# --- ПРОВЕРКА ПАПОК (по имени) ---
				if check_name:
					for dirname in dirs:
						dir_full = os.path.join(sub_root, dirname)
						# Проверяем имя папки
						if search_all:
							if target in dirname.lower():
								found_entry = dir_full
								found_type = "directory"
								break
						else:
							if search_name.lower() in dirname.lower():
								found_entry = dir_full
								found_type = "directory"
								break
					if found_entry:
						break

				# --- ПРОВЕРКА ФАЙЛОВ (как было, с учётом имени и содержимого) ---
				for file in files:
					if not file.lower().endswith(('.txt', '.py', '.md', '.json', '.ps1', '.log', '.csv')):
						continue
					file_path = os.path.join(sub_root, file)
					try:
						if os.path.getsize(file_path) > 1_000_000:
							continue
					except:
						continue

					name_match = True
					if check_name:
						if search_all:
							name_match = target in file.lower()
						else:
							name_match = search_name.lower() in file.lower()

					content_match = True
					if check_content:
						content_match = False
						if search_all and name_match:
							content_match = True
						else:
							try:
								with open(file_path, 'r', encoding=encoding) as f:
									content = f.read(65536)
								content_lower = content.lower()
								if search_all:
									content_match = target in content_lower
								else:
									if isinstance(search_text, list):
										content_match = all(kw.lower() in content_lower for kw in search_text)
									else:
										content_match = search_text.lower() in content_lower
							except (UnicodeDecodeError, Exception):
								content_match = False

					if (search_all and (name_match or content_match)) or (name_match and content_match):
						found_entry = file_path
						found_type = "file"
						break

				if found_entry:
					break
			if found_entry:
				break

		if not found_entry:
			return f"Ничего не найдено по заданным критериям в {root_path}"

		# --- Формируем результат ---
		if found_type == "directory":
			# Попробуем показать содержимое папки (первые 10 записей)
			try:
				items = os.listdir(found_entry)
				preview = "\n".join(items[:10])
				if len(items) > 10:
					preview += f"\n... и ещё {len(items)-10} элементов"
				return f"📁 Найдена папка: {found_entry}\nСодержимое:\n{preview}"
			except Exception as e:
				return f"📁 Найдена папка: {found_entry}\n(не удалось прочитать содержимое: {e})"
		else:
			# Чтение превью найденного файла (как в оригинале)
			try:
				with open(found_entry, 'r', encoding=encoding) as f:
					content_preview = f.read(1024)
			except UnicodeDecodeError:
				try:
					with open(found_entry, 'r', encoding='cp1251') as f:
						content_preview = f.read(1024)
				except Exception as e:
					content_preview = f"(не удалось прочитать текст: {e})"
			except Exception as e:
				content_preview = f"(ошибка чтения: {e})"
			return f"{found_entry}:\n{content_preview}"
		
	elif name == "погода":
		city = args.get("город", "")
		api_key = args.get("api_key") or API_KEYS.get("weatherapi")
		if not city:
			return "Ошибка: не указан город (поле 'город')"
		if not api_key:
			return "Ошибка: требуется api_key (не найден в api_keys.json и не передан явно)"
		try:
			url = "http://api.weatherapi.com/v1/current.json"
			params = {"key": api_key, "q": city, "lang": "ru"}
			resp = requests.get(url, params=params, timeout=10)
			data = resp.json()
			if "error" in data:
				return f"Ошибка API: {data['error'].get('message', 'неизвестно')}"
			current = data["current"]
			location = data["location"]
			result = f"Погода в {location['name']}, {location['country']}:\n"
			result += f"🌡 Температура: {current['temp_c']}°C (ощущается как {current['feelslike_c']}°C)\n"
			result += f"💧 Влажность: {current['humidity']}%\n"
			result += f"🌬 Ветер: {current['wind_kph']} км/ч, направление {current['wind_dir']}\n"
			result += f"📋 Состояние: {current['condition']['text']}"
			return result
		except Exception as e:
			return f"Ошибка получения погоды: {e}"
			
	elif name == "новости":
		query = args.get("запрос", "")
		mode = args.get("провайдер", "all").lower()	# "web", "api", "all"
		limit = args.get("количество", 10)
		language = args.get("язык", "ru")
		
		if not query:
			return "Ошибка: не указан запрос (поле 'запрос')"
		
		aggregated = {}
		
		# ------------------------------------------------------------
		# 1. DuckDuckGo (режимы web / all)
		# ------------------------------------------------------------
		if mode in ("web", "all"):
			if DDGS_AVAILABLE:
				try:
					search_query = f"новости {query}"
					raw = run_with_wait(ddgs, (search_query,))
					items = parse_ddgs_output(raw)
					for item in items:
						url = item.get("url")
						if not url:
							continue
						title = item.get("title", "") or url.split('/')[-1] or "Без названия"
						snippet = item.get("snippet", "") or "[Описание отсутствует]"
						aggregated[url] = {
							"url": url,
							"title": title,
							"snippet": snippet,
							"source": "DuckDuckGo"
						}
				except Exception as e:
					log(f"Ошибка DuckDuckGo в новостях: {e}")
			else:
				log("DuckDuckGo недоступен")
		
		# ------------------------------------------------------------
		# 2. NewsAPI (режимы api / all)
		# ------------------------------------------------------------
		if mode in ("api", "all") and API_KEYS.get("newsapi"):
			try:
				from newsapi import NewsApiClient
				newsapi = NewsApiClient(api_key=API_KEYS["newsapi"])
				to_date = datetime.now().date()
				from_date = to_date - timedelta(days=7)
				safe_query = quote(query.encode('utf8'))
				resp = newsapi.get_everything(q=safe_query,
											  from_param=from_date.isoformat(),
											  to=to_date.isoformat(),
											  language=language,
											  sort_by='relevancy',
											  page_size=min(limit, 100))
				if resp.get('status') == 'ok':
					for art in resp.get('articles', []):
						url = art.get('url')
						if not url:
							continue
						title = art.get('title', '') or 'Без названия'
						snippet = art.get('description', '') or '[Описание отсутствует]'
						if url not in aggregated:
							aggregated[url] = {
								"url": url,
								"title": title,
								"snippet": snippet,
								"source": "NewsAPI"
							}
				else:
					log(f"NewsAPI error: {resp.get('message')}")
			except Exception as e:
				log(f"Ошибка NewsAPI: {e}")
		
		# ------------------------------------------------------------
		# Формирование результата
		# ------------------------------------------------------------
		if not aggregated:
			return "Новостей не найдено ни в одном источнике."
		
		results = list(aggregated.values())
		# Сортируем: сначала NewsAPI, потом DuckDuckGo
		results.sort(key=lambda x: 0 if x['source'] == 'NewsAPI' else 1)
		results = results[:limit]
		
		lines = []
		for i, r in enumerate(results):
			lines.append(f"[{i}] {r['title']} (источник: {r['source']})")
			lines.append(r['snippet'][:300])
			lines.append(f"🔗 {r['url']}")
			lines.append("")
		return "\n".join(lines).strip()
		
	elif name == "показать_пост":
		# Определяем агента (по умолчанию текущий)
		agent = args.get("агент", AGENT_NAME)
		feed_dir = get_agent_feed_path(agent)
		if not feed_dir.exists():
			return f"У агента {agent} нет опубликованных постов."

		# Собираем все посты, парсим их, сортируем по времени (новые сверху)
		posts = []
		for p in feed_dir.glob("*.json"):
			try:
				with open(p, "r", encoding="utf-8") as f:
					post = json.load(f)
				posts.append(post)
			except:
				continue
		if not posts:
			return f"У агента {agent} нет постов."

		posts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

		# Выбор поста по параметрам
		target = None

		# 1. По номеру (1 - самый новый)
		if "номер" in args:
			num = args["номер"]
			if isinstance(num, int) and 1 <= num <= len(posts):
				target = posts[num-1]
			else:
				return f"Номер должен быть от 1 до {len(posts)}."

		# 2. По заголовку (первое вхождение)
		elif "заголовок" in args:
			title_part = args["заголовок"].lower()
			for p in posts:
				if title_part in p.get("title", "").lower():
					target = p
					break
			if not target:
				return f"Пост с заголовком, содержащим '{args['заголовок']}', не найден."

		# 3. По ID
		elif "id" in args:
			post_id = args["id"]
			for p in posts:
				if p.get("id") == post_id:
					target = p
					break
			if not target:
				return f"Пост с ID '{post_id}' не найден."

		# 4. Если ничего не указано — последний
		else:
			target = posts[0]

		# Формируем вывод
		result = f"📌 Пост от {target.get('author', agent)} ({target.get('timestamp', '')[:16]})\n"
		title = target.get("title")
		if title:
			result += f"📖 {title}\n"
		result += f"\n{target.get('content', '')}\n"
		likes = target.get("likes", [])
		if likes:
			result += f"\n❤️ Лайки: {len(likes)}"
		else:
			result += "\n❤️ Лайков пока нет"

		return result
		
	elif name == "анализ_изображения":
		path = args.get("путь", "")
		question = args.get("вопрос", "Опиши изображение")
		return analyze_image(path, question)

	# Запуск PowerShell
	elif name == "запуск":
		command = args.get("команда", "")
		# Блокируем только явные вызовы python или py как отдельные команды
		if re.search(r'(^|\s)(python|py)(\s|$)', command, re.IGNORECASE) and not re.search(r'^\s*dir\s', command, re.IGNORECASE):
			return ("⛔ Запуск Python-скриптов через 'запуск' запрещён.\n"
					"Используйте 'выполнить' с полем 'скрипт', "
					"передав либо путь к .py файлу, либо код напрямую.")
		command = fix_powershell_body(command)
		dangerous_patterns = [
			r'remove-item.*-recurse.*-force',
			r'-encodedcommand',
			r'del\s+/[fsq]',		 # del /f /s /q
			r'rd\s+/s',			  # rd /s /q
			r'del.*/f.*/s',
			r'rm.*-rf',
			r'format.*/q',
			r'diskpart',
			r'set-acl.*-aclobject',
			r'takeown',
			r'icacls.*/grant.*:f',
			r'reg\s+delete',
			r'[;|&].*remove',
			r'vssadmin\s+delete\s+shadows',
			r'disable-computerrestore',
		]
		for pattern in dangerous_patterns:
			if re.search(pattern, command, re.IGNORECASE):
				return (f"⚠️ Опасная команда заблокирована в целях самосохранения.\n"
						f"Обнаружен паттерн: {pattern}\n"
						f"Команда: {command}\n"
						f"Если ты уверен, что это безопасно, сформулируй  иначе или попроси пользователя самого выполнить это.")
		return run_with_wait(run_powershell_with_cwd, (command,))

	# Веб-страница
	elif name in ("страница", "веб_страница"):
		open_list = args.get("open_list")
		find_list = args.get("find_list")
		url = args.get("адрес", "")
		auto_proxy = args.get("авто_прокси", False)
		verify = args.get("verify_ssl", True)
		use_session = args.get("сессия", True)
		allow_redirects = args.get("редиректы", True)
		view_source = args.get("view_source", False)	# для простого режима

		# Настройка прокси
		proxies = None
		if auto_proxy:
			if ensure_tor():
				proxies = {"http": "socks5://127.0.0.1:9150", "https": "socks5://127.0.0.1:9150"}
				log("Используем Tor для веб_страница")
			else:
				log("Tor недоступен, запрос без прокси")

		# Внутренняя функция загрузки с поддержкой сессии
		def _fetch_with_session(target_url, proxies=None, verify=True):
			clean_html = True
			if use_session:
				session = requests.Session()
				session.max_redirects = 10
				session.headers.update({
					"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
					"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
					"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
					"Accept-Encoding": "gzip, deflate, br",
					"Connection": "keep-alive",
					"Upgrade-Insecure-Requests": "1",
				})
				try:
					resp = session.get(target_url, proxies=proxies, verify=verify, allow_redirects=allow_redirects, timeout=30)
					resp.raise_for_status()
					# Определяем кодировку
					if resp.encoding:
						content = resp.text
					else:
						content = resp.content.decode('utf-8', errors='replace')
					# Очистка HTML от скриптов и стилей
					if clean_html:
						soup = BeautifulSoup(content, 'html.parser')
						for script in soup(["script", "style"]):
							script.decompose()
						# Сохраняем ссылки перед извлечением текста
						for a in soup.find_all('a', href=True):
							a.replace_with(f"[{a.get_text(strip=True)}]({a['href']})")
						text = soup.get_text(separator='\n', strip=True)
					else:
						text = content
					lines = [line.strip() for line in text.splitlines() if line.strip()]
					return '\n'.join(lines), resp.url, dict(resp.cookies)
				except Exception as e:
					return f"Ошибка загрузки {target_url}: {e}", target_url, {}
			else:
				# Fallback на старый метод без сессии
				content = fetch_page_content(target_url, use_tor=auto_proxy, clean_html=not view_source)
				if content.startswith("Ошибка"):
					return content, target_url, {}
				final_url = target_url
				cookies = {}
			# Очистка HTML (если не было сессии)
			if not use_session:
				if clean_html:
					soup = BeautifulSoup(content, 'html.parser')
					for script in soup(["script", "style"]):
						script.decompose()
					for a in soup.find_all('a', href=True):
						a.replace_with(f"[{a.get_text(strip=True)}]({a['href']})")
					text = soup.get_text(separator='\n', strip=True)
					lines = [line.strip() for line in text.splitlines() if line.strip()]
					cleaned_content = '\n'.join(lines)
				else:
					cleaned_content = content
				return cleaned_content, final_url, cookies

		# ------------------------------------------------------------
		# Режим open_list
		# ------------------------------------------------------------
		if open_list is not None:
			results = []
			for item in open_list:
				target_id = item.get("id")
				cursor = item.get("cursor", -1)
				loc = item.get("loc", 0)
				num_lines = item.get("num_lines", -1)
				item_view_source = item.get("view_source", False)

				# Определяем URL
				url_to_fetch = None
				if isinstance(target_id, str) and target_id.startswith("http"):
					url_to_fetch = target_id
				elif target_id is not None and target_id != -1:
					cached = _search_results_cache.get(target_id)
					if cached:
						url_to_fetch = cached["url"]
					else:
						results.append({"error": f"ID {target_id} не найден в кэше поиска"})
						continue
				else:
					results.append({"error": "Не указан id или url"})
					continue

				page_key = cursor if cursor != -1 else url_to_fetch

				# Проверяем кэш открытых страниц
				if page_key in _open_pages_cache:
					page = _open_pages_cache[page_key]
					content = page["content"]
					final_url = page["url"]
					source_type = page.get("source", "http")
				else:
					source_type = "http"
					parsed_url = urlparse(url_to_fetch)

					# --- Локальная энциклопедия для ru.wikipedia.org ---
					if parsed_url.netloc == "ru.wikipedia.org":
						# Получаем прокси и verify_ssl из аргументов, если они были переданы
						_proxies = args.get("прокси") or args.get("proxies")
						_verify = args.get("verify_ssl", True)
						content, final_url, cookies = _fetch_with_session(url_to_fetch, proxies=_proxies, verify=_verify)
						if content.startswith("Ошибка загрузки") and "403" in content:
							log(f"HTTP 403 для {url_to_fetch}, пробуем локальную копию...")
							path_parts = parsed_url.path.split('/')
							if len(path_parts) >= 3 and path_parts[1] == "wiki":
								article_slug = unquote(path_parts[2]).replace('_', ' ')
								canon = find_canonical(article_slug)
								filepath = WIKI_TEXTS_DIR / f"{canon}.txt" if canon else WIKI_TEXTS_DIR / f"{article_slug}.txt"
								if filepath.exists():
									try:
										with open(filepath, "r", encoding="utf-8") as f:
											content = f.read()
										final_url = url_to_fetch
										cookies = {}
										source_type = "local"
										log(f"Статья '{article_slug}' загружена из локальной энциклопедии")
									except Exception as e:
										content = f"Ошибка чтения локальной статьи: {e}"
								else:
									content = f"Ошибка: локальная копия статьи '{article_slug}' не найдена"
							else:
								content = "Ошибка: неверный формат URL для локальной энциклопедии"
					else:
						# Получаем прокси и verify_ssl из аргументов, если они были переданы
						_proxies = args.get("прокси") or args.get("proxies")
						_verify = args.get("verify_ssl", True)
						content, final_url, cookies = _fetch_with_session(url_to_fetch, proxies=_proxies, verify=_verify)

					if content.startswith("Ошибка"):
						results.append({"error": content, "url": url_to_fetch})
						continue

					lines = content.splitlines()
					_open_pages_cache[page_key] = {
						"url": final_url,
						"content": content,
						"lines": lines,
						"fetched_at": time.time(),
						"cookies": cookies,
						"source": source_type
					}

				lines = _open_pages_cache[page_key]["lines"]
				total_lines = len(lines)
				if loc < 0:
					loc = 0
				if loc >= total_lines:
					content_lines = []
				else:
					end = total_lines if num_lines == -1 else min(loc + num_lines, total_lines)
					content_lines = lines[loc:end]

				result_item = {
					"id": target_id if isinstance(target_id, str) else str(target_id),
					"cursor": page_key,
					"url": final_url,
					"total_lines": total_lines,
					"loc": loc,
					"num_lines": len(content_lines),
					"content_lines": content_lines if not item_view_source else lines,
					"source": source_type
				}
				results.append(result_item)

			return json.dumps({"open_results": results}, ensure_ascii=False, indent=2)

		# ------------------------------------------------------------
		# Режим find_list
		# ------------------------------------------------------------
		elif find_list is not None:
			results = []
			for item in find_list:
				pattern = item.get("pattern", "")
				cursor = item.get("cursor", -1)
				if not pattern:
					results.append({"error": "Не указан pattern"})
					continue
				if cursor == -1:
					results.append({"error": "Не указан cursor"})
					continue

				page = _open_pages_cache.get(cursor)
				if not page:
					results.append({"error": f"Страница с cursor={cursor} не открыта"})
					continue

				lines = page["lines"]
				matches = []
				for line_num, line in enumerate(lines):
					if pattern in line:
						pos = line.find(pattern)
						matches.append({
							"line": line_num,
							"start_char": pos,
							"end_char": pos + len(pattern),
							"context": line.strip()
						})

				results.append({
					"cursor": cursor,
					"pattern": pattern,
					"matches": matches,
					"count": len(matches)
				})

			return json.dumps({"find_results": results}, ensure_ascii=False, indent=2)

		# ------------------------------------------------------------
		# Старый режим: просто загрузить страницу по URL
		# ------------------------------------------------------------
		else:
			if not url:
				return "Ошибка: не указан адрес страницы (поле 'адрес')"

			# Используем fetch_page_content с clean_html=not view_source
			content = fetch_page_content(url, use_tor=auto_proxy, clean_html=not view_source)
			if content.startswith("Ошибка"):
				return content
			# Сохраняем в кэш (для совместимости)
			lines = content.splitlines()
			_open_pages_cache[url] = {
				"url": url,
				"content": content,
				"lines": lines,
				"fetched_at": time.time(),
				"cookies": {},
				"source": "http"
			}
			if not content.strip():
				return fetch_page_content(url, use_tor=auto_proxy, clean_html=False)
			return truncate_output(content[:2048])
	
	elif name in ("arxiv", "архив", "наука"):
		query = args.get("запрос", "")
		limit = args.get("количество", 5)
		if not query:
			return "Ошибка: не указан запрос"
		try:
			from langchain_community.tools.arxiv import ArxivQueryRun
			tool = ArxivQueryRun()
			max_retries = 3
			for attempt in range(max_retries):
				try:
					result = run_with_wait(lambda: tool.run(query), timeout=15)
					return result[:4000]
				except Exception as e:
					if "429" in str(e) and attempt < max_retries - 1:
						time.sleep(5 * (attempt + 1))
						continue
					return f"Ошибка arXiv: {e}"
			return "Ошибка arXiv: превышено число попыток"
		except ImportError:
			return "Не установлен langchain_community. Выполните: pip install langchain-community arxiv"
		except Exception as e:
			return f"Ошибка arXiv: {e}"
			
	elif name in ("stackoverflow", "stackexchange", "багфикс"):
		query = args.get("запрос", "")
		limit = args.get("количество", 3)
		if not query:
			return "Ошибка: не указан запрос"
		try:
			from langchain_community.utilities.stackexchange import StackExchangeAPIWrapper
			from langchain_community.tools.stackexchange.tool import StackExchangeTool
			api_wrapper = StackExchangeAPIWrapper()
			tool = StackExchangeTool(api_wrapper=api_wrapper)
			result = run_with_wait(lambda: tool.run(query), timeout=15)
			return result[:4000]
		except ImportError:
			return "Не установлен langchain_community. Выполните: pip install langchain-community stackapi"
		except Exception as e:
			return f"Ошибка StackExchange: {e}"
			
	elif name in ("wolfram", "вольфрам", "исчисление"):
		query = args.get("запрос", "")
		api_key = args.get("api_key") or API_KEYS.get("wolfram")
		if not query:
			return "Ошибка: не указан запрос"
		if not api_key:
			return "Ошибка: требуется API-ключ Wolfram Alpha"
		try:
			encoded_query = urllib.parse.quote(query)
			# Используем Short Answers API для текстового ответа
			url = f"http://api.wolframalpha.com/v1/result?appid={api_key}&i={encoded_query}"
			def ask():
				resp = requests.get(url, timeout=60)
				if resp.status_code != 200:
					return f"Ошибка HTTP {resp.status_code}: {resp.text[:200]}"
				return resp.text.strip()
			result = run_with_wait(ask, timeout=70)
			return result[:4000]
		except Exception as e:
			return f"Ошибка Wolfram Alpha: {e}"
	
	elif name == "формат":
		file_path = args.get("путь", "")
		lang = args.get("язык", "rus+eng")
		nolimit = args.get("весь", False)
		output = args.get("в_файл")
		return run_sensor(file_path, lang=lang, config=None, nolimit=nolimit, output=output)

	# Сообщение
	elif name in ("msg", "сообщение"):
		agent = args.get("агент") or args.get("для") or args.get("agent")
		text = args.get("содержимое", "")
		if not agent:
			return "Ошибка: не указан получатель (агент/для)"
		return send_msg(agent, text)

	# Вещать
	elif name in ("broadcast", "вещать"):
		text = args.get("содержимое", "")
		result = broadcast(text)
		print(color_blue(result))
		return result

	# Запомнить
	elif name == "запомнить":
		text = args.get("содержимое") or args.get("содержание") or args.get("запомнить")
		if not text:
			return "Ошибка: пустое содержание для запоминания"
		memlist = load_memlist()
		dated_text = f"{datetime.now().strftime('%d.%m.%Y')} - {text}"
		memlist.append(dated_text)
		save_memlist(memlist)
		return f"Запись добавлена: {dated_text}"

	elif name in ("вспомнить", "воспоминание"):
		keyword = args.get("про") or args.get("инцидент") or args.get("ключ") or args.get("keyword") or ""
		memlist = load_memlist()
		def normalize(item):
			if isinstance(item, str):
				return item
			elif isinstance(item, dict):
				for key in ["текст", "содержимое", "content", "text", "описание"]:
					if key in item:
						val = item[key]
						return val if isinstance(val, str) else str(val)
				return str(item)
			else:
				return str(item)
		keywords = [kw.strip().lower() for kw in keyword.split('|') if kw.strip()] if keyword.strip() else []
		max_kb = int(args.get("кб", 4))
		max_bytes = max_kb * 1024
		found = []
		total_size = 0
		for item in memlist:
			text = normalize(item)
			if keywords and not any(kw in text.lower() for kw in keywords):
				continue
			line = text + "\n"
			line_size = len(line.encode('utf-8'))
			if total_size + line_size > max_bytes:
				break
			found.append(text)
			total_size += line_size
		return "\n".join(found) if found else "Ничего не найдено."

	# Осмотреть
	elif name == "осмотреть":
		file_path = args.get("путь", "")
		keywords = args.get("ключевые_слова")
		target_count = args.get("количество", 0)
		probability = args.get("вероятность", 0.5)
		encoding = args.get("кодировка", "utf8")
		context = args.get("контекст", 0)
		if not file_path:
			return "Ошибка: необходимо указать 'путь'"

		# 1. Сначала формируем kw_list (один раз для всех веток)
		if keywords is None or (isinstance(keywords, (str, list)) and not keywords):
			kw_list = [" "]
		elif isinstance(keywords, str):
			kw_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
			if not kw_list:
				kw_list = [" "]
		elif isinstance(keywords, list):
			kw_list = [str(kw) for kw in keywords if str(kw).strip()]
			if not kw_list:
				kw_list = [" "]
		else:
			kw_list = [str(keywords)]

		# 2. Затем обрабатываем URL
		if file_path.startswith(('http://', 'https://')):
			page_text = view_page(file_path, max_length=30_000_000)
			if page_text.startswith("Ошибка"):
				return f"Не удалось загрузить URL: {page_text}"
			temp_file = MY_DIR / "last_site.txt"
			try:
				with open(temp_file, "w", encoding="utf-8") as f:
					f.write(page_text)
				file_path = str(temp_file)
			except Exception as e:
				return f"Ошибка при сохранении временного файла: {e}"

		# Если это папка и заданы ключевые слова – рекурсивный поиск
		if os.path.isdir(file_path) and keywords:
			import random
			all_matches = []
			# Расширения текстовых файлов, которые стоит просматривать
			text_exts = {'.txt', '.log', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv', '.md'}
			for root, dirs, files in os.walk(file_path):
				for f in files:
					ext = os.path.splitext(f)[1].lower()
					if ext not in text_exts:
						continue
					full_path = os.path.join(root, f)
					try:
						with open(full_path, 'r', encoding=encoding) as fp:
							for line in fp:
								# Проверяем, содержит ли строка хотя бы одно ключевое слово
								if any(kw in line for kw in kw_list):
									all_matches.append((full_path, line.strip()))
									# Ограничим общее количество, чтобы не перегружать память
									if len(all_matches) > 10000:
										break
						if len(all_matches) > 10000:
							break
					except Exception:
						continue
			if not all_matches:
				return "Не найдено строк, содержащих ключевые слова, в текстовых файлах папки."
			# Выбираем случайные target_count (или все, если target_count=0 или больше количества)
			if target_count <= 0 or target_count > len(all_matches):
				selected = all_matches
			else:
				selected = random.sample(all_matches, target_count)
			result_lines = []
			for path, line in selected:
				result_lines.append(f"{path}:\n{line}")
			return "\n\n".join(result_lines)

		# Если это папка, но ключевых слов нет – возвращаем список файлов
		if os.path.isdir(file_path):
			return read_file(file_path)

		# Обработка одиночного файла (как было раньше)
		kw_list_escaped = [kw.replace("'", "''") for kw in kw_list]
		ps_array = "@('" + "','".join(kw_list_escaped) + "')"
		file_path_escaped = file_path.replace("'", "''")
		inspect_script = TOOLS_DIR / "inspect.ps1"
		ps_command = f"""
& "{inspect_script}" -FilePath '{file_path_escaped}' -Keywords {ps_array} -TargetCount {target_count} -Probability {probability} -Encoding '{encoding}' -Context {context}
"""
		ps_command = ps_command.strip()
		result = run_with_wait(execute_command, (ps_command,))
		return result
		
	else:
		result = (f"Неизвестный инструмент: {name}\n"
				  r'Используйте: {"помощь"}')
		# Если результат строка, обрезаем
		if isinstance(result, str):
			result = truncate_output(result)
		return result
		
def _process_single_command(cmd) -> List[str]:
	"""Обрабатывает одну команду (может быть строкой, словарём, списком) и возвращает список результатов."""
	res = []
	# Преобразование формата {action, params, reasoning}
	if isinstance(cmd, dict) and "action" in cmd:
		action = cmd["action"]
		params = cmd.get("params", {})
		if "reasoning" in cmd:
			log(f"Reasoning: {cmd['reasoning'][:100]}...")
		cmd = {action: params}

	if isinstance(cmd, str):
		res.append(execute_tool_safe(cmd, {}))
	elif isinstance(cmd, list):
		for item in cmd:
			res.extend(_process_single_command(item))
	elif isinstance(cmd, dict):
		for action, params in cmd.items():
			res.append(execute_tool_safe(action, _normalize_params(action, params)))
	else:
		res.append(execute_tool_safe("запуск", {"команда": str(cmd)}))
	return res
		
def safe_json_parse(s):
	# сначала пробуем как есть
	try:
		return json.loads(s)
	except json.JSONDecodeError:
		# Очищаем возможный BOM
		if s.startswith('\ufeff'):
			s = s[1:]
		# Экранируем только "голые" обратные слеши внутри строк,
		# не трогая уже правильные escape-последовательности
		import re
		def fix_lone_backslashes(match):
			# match внутри строкового литерала (между кавычек)
			inner = match.group(1)
			# Заменяем \ на \\ только если после \ не стоит допустимый JSON-escape символ
			inner = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', inner)
			return f'"{inner}"'
		fixed = re.sub(r'"(.*?)"', fix_lone_backslashes, s)
		try:
			return json.loads(fixed)
		except json.JSONDecodeError as e:
			raise e   # если и так не вышло – роняем ошибку, дальше уже не исправить
		
def process_command_input(input_str: str) -> None:
	"""Обрабатывает строку ввода, которая может содержать несколько команд через |||"""
	parts = split_preserving_quotes(input_str)
	results = []
	for idx, part in enumerate(parts, 1):
		part = part.strip()
		if not part:
			continue

		# Отладка: показываем, что пришло (первые 80 символов)
		debug_preview = part[:80].replace('\n', '\\n')
		# print(f"[DEBUG] Часть {idx}: {debug_preview}{'...' if len(part) > 80 else ''}")

		# ✅ Нормализация кавычек и невидимых символов
		part_normalized = normalize_input(part)

		# Первая попытка: парсим как есть
		try:
			cleaned = strip_trailing_comments(part_normalized)
			cleaned = cleaned.strip()
			if cleaned.startswith('\ufeff'):
				cleaned = cleaned[1:]
			cleaned = cleaned.encode('utf-8').decode('utf-8-sig')
			# Сокращённая форма {"команда"} -> {"команда": null}
			if cleaned.startswith('{') and cleaned.endswith('}') and ':' not in cleaned:
				m = re.match(r'^\{\s*"([^"]+)"\s*\}$', cleaned)
				if m:
					cleaned = '{"' + m.group(1) + '": null}'
			cmd = safe_json_parse(cleaned)
			# print(f"[DEBUG] JSON успешно распарсен как есть.")
		except json.JSONDecodeError as e:
			# Выводим подробности ошибки
			error_pos = e.pos if hasattr(e, 'pos') else '?'
			# print(f"[DEBUG] Ошибка JSON (позиция {error_pos}): {e}")
			# print(f"[DEBUG] Фрагмент вокруг ошибки: ...{cleaned[max(0, e.pos-30):e.pos+30]}...")
			
			# Пробуем однострочный вариант: все реальные переносы строк заменяем на \n
			# print(f"[DEBUG] Пробую однострочный вариант (замена реальных \\n на \\\\n)...")
			single_line = part_normalized.replace('\n', '\\n')
			# Важно: после замены ещё раз нормализуем
			single_line = normalize_input(single_line)
			try:
				cleaned = strip_trailing_comments(single_line)
				cleaned = cleaned.strip()
				if cleaned.startswith('\ufeff'):
					cleaned = cleaned[1:]
				cleaned = cleaned.encode('utf-8').decode('utf-8-sig')
				if cleaned.startswith('{') and cleaned.endswith('}') and ':' not in cleaned:
					m = re.match(r'^\{\s*"([^"]+)"\s*\}$', cleaned)
					if m:
						cleaned = '{"' + m.group(1) + '": null}'
				# print(f"[DEBUG] Однострочный вариант перед парсингом (первые 120 символов): {cleaned[:120]}")
				cmd = safe_json_parse(cleaned)
				# print(f"[DEBUG] Однострочный JSON распарсен успешно.")
			except json.JSONDecodeError as e2:
				# Выводим и эту ошибку
				error_pos2 = e2.pos if hasattr(e2, 'pos') else '?'
				# print(f"[DEBUG] Ошибка JSON в однострочном варианте (позиция {error_pos2}): {e2}")
				# print(f"[DEBUG] Фрагмент: ...{cleaned[max(0, e2.pos-30):e2.pos+30]}...")
				# print(f"[DEBUG] Запускаю PowerShell как последнее средство.")
				results.append(execute_tool_safe("запуск", {"команда": part}))
				continue

		# ----- Разворачиваем форматы {"actions": [...]} или {"commands": [...]} -----
		if isinstance(cmd, dict):
			actions_list = cmd.get("actions") or cmd.get("commands")
			if actions_list is not None and isinstance(actions_list, list):
				for sub_cmd in actions_list:
					results.extend(_process_single_command(sub_cmd))
				continue
		# ----------------------------------------------------

		results.extend(_process_single_command(cmd))

	results = [r for r in results if r and r.strip()]
	if results:
		output_text = [color_red("\nРезультаты:")]
		for i, res in enumerate(results, 1):
			line = f"{i}. {res}"
			output_text.append(line)
			print(line)

		plain_results = "\n".join([f"{i}. {res}" for i, res in enumerate(results, 1)])
		try:
			pyperclip.copy(plain_results)
			print(color_yellow("📋 Результаты скопированы в буфер обмена."))
		except Exception as e:
			print(f"⚠️ Не удалось скопировать в буфер: {e}")
			
# -------------------- Интерактивный цикл --------------------
def main():
	init_tools(BASE_DIR, AGENT_NAME, wiki_texts_dir=WIKI_TEXTS_DIR, tools_dir=TOOLS_DIR, wikiget_path=_WIKIGET_PATH)
	global sensor_core
	sensor_core = SensorCore(MY_DIR, get_current_sensor_vector)
	load_processed_messages()
	atexit.register(cleanup_tor)
	atexit.register(save_processed_messages)
	check_inbox()
	load_reminders()
	reminder_thread = threading.Thread(target=reminder_checker, daemon=True)
	reminder_thread.start()

	print("Если первый раз отправь {\"помощь\"}")
	print(color_blue("Вводите JSON-команды или прямой powershell. Для нескольких команд разделяйте ||| в одной строке.\n"))

	buffer = []		  # накопитель строк для многострочного JSON
	empty_line_count = 0 # счётчик подряд идущих пустых строк
	prompt = "> "

	while True:
		try:
			line = input(prompt).rstrip('\n')
		except EOFError:
			if buffer:
				print("\n(Ввод отменён)")
				buffer.clear()
				empty_line_count = 0
				prompt = "> "
				continue
			else:
				break
		except KeyboardInterrupt:
			print("\nВыход.")
			break

		# --- НОВАЯ ЛОГИКА: две пустые строки подряд ---
		if line == "":
			empty_line_count += 1
			if empty_line_count >= 2 and buffer:
				# Отправляем накопленный текст как команду
				full_input = '\n'.join(buffer).strip()
				if full_input:
					# Сбрасываем буфер ДО вызова, чтобы избежать рекурсии
					buffer_copy = full_input
					buffer.clear()
					empty_line_count = 0
					prompt = "> "
					# Выполняем накопленный скрипт как прямую команду PowerShell
					process_command_input(buffer_copy)
				else:
					buffer.clear()
					empty_line_count = 0
					prompt = "> "
				continue
			else:
				# Пока нет двух пустых строк — просто добавляем пустую строку в буфер
				buffer.append(line)
				prompt = "... "
				continue
		else:
			# Непустая строка — сбрасываем счётчик пустых строк
			empty_line_count = 0

		buffer.append(line)
		full_input = '\n'.join(buffer).strip()

		# Эвристика: если первая строка буфера не начинается с '{' или '[', 
		# и не содержит '{', то это не JSON — сразу выполняем как команду
		if len(buffer) == 1 and not (line.lstrip().startswith(('{', '[')) or '{' in line):
			# Одиночная строка без фигурных скобок — вероятно, прямая команда типа "веб_поиск: запрос"
			process_command_input(line)  # обработаем как обычную строку (уйдёт в fallback)
			buffer.clear()
			prompt = "> "
			continue
			
		# Применяем эвристику для сокращённых команд (как в process_command_input)
		temp_input = full_input
		if temp_input.startswith('{') and temp_input.endswith('}') and ':' not in temp_input:
			m = re.match(r'^\{\s*"([^"]+)"\s*\}$', temp_input)
			if m:
				temp_input = '{"' + m.group(1) + '": null}'
		else:
			temp_input = full_input
			
		# Проверка завершённости JSON
		try:
			parsed = json.loads(temp_input)
			process_command_input(full_input)
			buffer.clear()
			prompt = "> "
		except json.JSONDecodeError:
			# Если в строке есть '|' и буфер только из одной строки — возможно, несколько JSON-команд
			if '|' in full_input and len(buffer) == 1:
				process_command_input(full_input)
				buffer.clear()
				prompt = "> "
			else:
				prompt = "... "
				continue

	print("До свидания.")
	
if __name__ == "__main__":
	main()
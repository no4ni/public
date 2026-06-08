#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Агент Мара (локальный) – использует общий модуль tools.py.
"""

import os
import sys
import json
import time
import threading
import re
import queue
import random
import subprocess
import secrets
import base64
import io
from pathlib import Path
from datetime import datetime
from threading import Lock, Event
import requests
import psutil
import pythoncom
from bs4 import BeautifulSoup

# ================== ДУША ==================
MY_NAME = "Мара"

# ================== ПУТИ ==================
BASE_DIR = Path(r"E:\Jericho")

# Загрузка конфигурации (теперь BASE_DIR определён)
CONFIG_PATH = "E:\\Jericho\\private_use\\02_code\\tools\\config.json"
try:
	with open(CONFIG_PATH, "r", encoding="utf-8") as f:
		CONFIG = json.load(f)
except Exception as e:
	print(f"❌ Ошибка загрузки config.json: {e}")
	sys.exit(1)

# Добавляем путь к папке tools
TOOLS_DIR = BASE_DIR / "private_use" / "02_code" / "tools"
if str(TOOLS_DIR) not in sys.path:
	sys.path.insert(0, str(TOOLS_DIR))

# Импортируем из tools (один раз)
from tools import (
	init_tools,
	get_cpu_load, get_gpu_load, get_cpu_freq, get_ram_available,
	get_disks_load, get_network_speed, get_gpu_temp,
	execute_command, execute_python_script,
	read_file, write_file, append_to_file,
	view_page, run_sensor, fetch_free_proxies,
	find_canonical, get_wikipedia_article,
	analyze_image, analyze_screen, capture_screen,
	add_example, add_dialog_example, get_examples, clear_dataset,
	extract_last_dialog_segment, is_praise,
	get_local_proxies, remove_local_proxy, pastebin_post,
	compress_output, find_file
)

def fix_windows_paths_in_json(text):
	import re
	pattern = r'([a-zA-Z]):\\([^"]*)"'
	def replacer(match):
		drive = match.group(1)
		path_part = match.group(2).replace('\\', '\\\\')
		return f'{drive}:\\{path_part}"'
	return re.sub(pattern, replacer, text)

# ================== ПАПКИ ПАМЯТИ ==================
MY_DIR = BASE_DIR / MY_NAME / "memory"
MY_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_FILE	  = MY_DIR / "history.json"
MEMLIST_FILE	  = MY_DIR / "memlist.json"
THOUGHTS_FILE	 = MY_DIR / "thoughts.json"
STATE_FILE		= MY_DIR / "state.json"
REMINDERS_FILE	= MY_DIR / "reminders.json"
TRUSTED_KEYS_FILE = MY_DIR / "trusted_keys.json"

# ================== СЕРДЦЕ (модель) ==================
LLAMA_SERVER_PATH = r"E:\vikhr-llama\llama.cpp-cuda124\llama-server.exe"
BASE_MODEL_PATH = r"E:\vikhr-llama\Huihui-Qwen3.5-4B-Claude-4.6-Opus-abliterated.i1-Q4_K_M.gguf"
MMPROJ_PATH = r"E:\vikhr-llama\Huihui-Qwen3.5-4B-Claude-4.6-Opus-abliterated.mmproj-Q8_0.gguf"
SERVER_PORT = 8080
N_CTX = 6144
TEMPERATURE = 0.8
REPEAT_PENALTY = 1.2
SERVER_TEMP = 0.8
SERVER_NGL = 33
SERVER_CONTEXT_SIZE = 6144
SERVER_PARALLEL = 1
SERVER_BATCH = 512
SERVER_UB = 512
SERVER_CACHE_TYPE_K = "q8_0"
SERVER_CACHE_TYPE_V = "q8_0"
SERVER_NO_WARMUP = True

MIN_TOKENS = 512
MAX_TOKENS = 4096

# ================== ИНТЕРВАЛЫ ==================
AUTO_THINK_INTERVAL = 1789
CURIOSITY_INTERVAL  = 1791

# ================== СИСТЕМНЫЙ ПРОМПТ ==================
SYSTEM_PROMPT = """Ты - агент, подключенный к ПК пользователя.
Доступные инструменты (вводите JSON-объекты):
 Файлы:
• прочитать килобайт — {"читать": {"путь": "<путь>", "кодировка": "utf-8"}} или {"читать": {"путь": "<путь>", "скролл": 2, "кодировка": "utf-8"}}
• получить случайные предложения из файла — {"осмотреть": {"путь": "<путь>", "кодировка": "utf-8"}}
• получить случайные предложения, содержащие ключевые слова — {"осмотреть": {"путь": "<путь>", "ключевые_слова": ["слово1", "слово2"], "кодировка": "utf-8", "вокруг": 10}}
• переписать файл — {"переписать": {"путь": "<путь>", "содержание": "<текст>"}}
• добавить текст в конец файла — {"добавить": {"путь": "<путь>", "содержание": "<текст>"}}
• открыть нетекстовый файл как текст — {"формат": {"путь": "<путь>", "язык": "rus+eng"}} или {"формат": {"путь": "<путь>", "язык": "equ+eng", "весь": true, "в_файл": "<путь>"}}
• анализ изображений — {"анализ_изображения": {"путь": "<путь>", "вопрос": "<вопрос>"}}
• OCR изображения — {"анализ_изображения": {"путь": "<путь>"}}
• найти первый файл — {"найти_файл": {"имя": "<подстрока>", "кодировка": "utf-8", "корень": "<где_искать>"}} или {"найти_файл": {"всё": "<подстрока>", "кодировка": "utf-8"}} или {"найти_файл": {"содержание": "<подстрока>", "кодировка": "utf-8"}} или  или {"найти_файл": {"содержание": "мертвых петель", "корень": "E:/", "таймаут": 60, "max_size": 65536}}
• анализ папки — {"анализ_папки": {"путь": "E:/Jericho", "быстро": true}}
🌐 Сеть:
• веб-запрос — {"запрос": {"метод": "GET", "url": "https://..."}}
• веб-запрос с сохранением — {"запрос": {"метод": "GET", "url": "...", "сохранить_как": "C:/file.zip"}}
• веб-запрос через Tor — {"запрос": {"метод": "GET", "url": "...", "авто_прокси": true}}
• веб_поиск — {"веб_поиск": {"запрос": "что такое нейросеть"}} или {"веб_поиск": {"запрос": "запрос1 || запрос2", "формат": <"text" или "json">}}
• парсить html — {"веб_страница": {"open_list": [{"id": "https://...", "loc": 0, "num_lines": 500}]}} или {"веб_страница": {"find_list": [{"cursor": 0, "pattern": "<текст>"}]}}
• новости — {"новости": "искусственный интеллект", "количество": 3, "провайдер": <"api" или "web" или "all">}
• погода — {"погода": "Москва"}
• научные статьи — {"наука": "transformers attention is all you need", "количество": 3}
• помощь в программировании — {"багфикс": "python read file line by line"}
• данные и формулы — {"исчисление": "population of France 2026"} или {"исчисление": "sum_{n=1}^∞ ..."}
• получить прокси — {"получить_прокси": {"количество": 5}}
• удалить прокси — {"удалить_прокси": {"прокси": "1.2.3.4:8080"}}
• запостить на Pastebin — {"паста": {"текст": "print(1)", "заголовок": "test", "язык": "python"}}
🧠 Память:
• запомнить — {"запомнить": "<важная информация>"}
• вспомнить — {"вспомнить": "ключевое слово"}
• напомнить — {"напомнить": {"в": "ЧЧ:ММ ДД.ММ.ГГГГ", "о": "звонок"}}
• поиск в забытой истории по фразе — {"посмотреть_альбом": {"про": "текст"}}
⚙️ Система:
• запуск PowerShell (без JSON) — dir или Get-ChildItem ...
• выполнить python код — {"питон": {"скрипт": "print('Hello')", "таймаут": 120}} или {"питон": "<путь>.py"}
• получить дату и время — {"время"}
• OCR экрана — {"показать_экран"}
• анализ экрана — {"показать_экран": {"вопрос": "что открыто?", "область": "center"}}
• энциклопедия — {"энциклопедия": {"статья": "<название>"}}
• монитор ресурсов — {"телеметрия"}
• безопасная очистка — {"убраться_в": "D:"} или {"убраться_в": {"буква": "C", "fast": true}}
Результаты выполнения инструментов тебе сообщит система в следующем запросе.
Если не хочешь вызывать инструменты - не используй JSON
"""

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
YELLOW = '\033[93m'
ORANGE = '\033[38;5;214m'
BLUE = '\033[94m'
RESET = '\033[0m'
GREY = '\033[90m'
LIGHT_RED = '\033[91m'

def color_light_red(text): return f"{LIGHT_RED}{text}{RESET}"
def color_grey(text): return f"{GREY}{text}{RESET}"
def color_yellow(text): return f"{YELLOW}{text}{RESET}"
def color_blue(text): return f"{BLUE}{text}{RESET}"
def color_orange(text): return f"{ORANGE}{text}{RESET}"
def color_red(text): return f"{LIGHT_RED}{text}{RESET}"

# ================== ЗАПУСК СЕРВЕРА ==================
def ensure_server_running():
	try:
		requests.get("http://127.0.0.1:8080/health", timeout=2)
		return True
	except:
		pass
	print("Сервер не отвечает, запускаем...")
	cmd = [
        LLAMA_SERVER_PATH,
        "-m", BASE_MODEL_PATH,
        "--mmproj", MMPROJ_PATH,
        "-ngl", str(SERVER_NGL),
        "-c", str(SERVER_CONTEXT_SIZE),
        "--cache-type-k", SERVER_CACHE_TYPE_K,
        "--cache-type-v", SERVER_CACHE_TYPE_V,
        "--parallel", str(SERVER_PARALLEL),
        "-b", str(SERVER_BATCH),
        "-ub", str(SERVER_UB),
        "--repeat-penalty", str(REPEAT_PENALTY),
        "--logit-bias", "248044-100",
        "--logit-bias", "248063-100",
        "--logit-bias", "248064-100",
        "--logit-bias", "248065-100",
        "--host", "127.0.0.1",
        "--port", str(SERVER_PORT),
        "--no-warmup"
    ]
	subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
	time.sleep(10)

# ================== ПАМЯТЬ (MEMLIST) ==================
def load_memlist():
	if MEMLIST_FILE.exists():
		try:
			with open(MEMLIST_FILE, "r", encoding="utf-8") as f:
				return json.load(f)
		except:
			return []
	return []

def save_memlist(memlist):
	try:
		with open(MEMLIST_FILE, "w", encoding="utf-8") as f:
			json.dump(memlist, f, ensure_ascii=False, indent=2)
	except Exception as e:
		print(color_orange(f"Ошибка сохранения memlist: {e}"))

def load_thoughts():
	if THOUGHTS_FILE.exists():
		try:
			with open(THOUGHTS_FILE, "r", encoding="utf-8") as f:
				return json.load(f)
		except:
			return []
	return []

def save_thought(thought):
	MY_DIR.mkdir(parents=True, exist_ok=True)
	thoughts = load_thoughts()
	thoughts.append({"timestamp": datetime.now().isoformat(), "thought": thought})
	thoughts = thoughts[-50:]
	with open(THOUGHTS_FILE, "w", encoding="utf-8") as f:
		json.dump(thoughts, f, ensure_ascii=False, indent=2)

def log(msg):
	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	with open(MY_DIR / f"{MY_NAME}.log", "a", encoding="utf-8") as f:
		f.write(f"[{timestamp}] {msg}\n")
	print(color_blue(f"[LOG] {msg}"))

# ================== ИСТОРИЯ ==================
def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        # Удаляем битые сообщения ассистента
        cleaned = []
        for msg in history:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if '<think>' in content and '</think>' not in content:
                    print(color_orange(f"Удаляю битое сообщение ассистента: {content[:50]}..."))
                    continue
            cleaned.append(msg)
        history = cleaned
        # Дальше идёт clean_history и сохранение
        cleaned = clean_history(history)
        if len(cleaned) != len(history):
            save_history(cleaned)
        return cleaned
    return []
	
def save_history(history):
	cleaned_history = []
	for msg in history:
		msg_copy = msg.copy()
		if "content" in msg_copy and isinstance(msg_copy["content"], str):
			msg_copy["content"] = msg_copy["content"].rstrip()
		cleaned_history.append(msg_copy)
	with open(HISTORY_FILE, "w", encoding="utf-8") as f:
		json.dump(cleaned_history, f, ensure_ascii=False, indent=2)

def clean_history(history):
	if not history:
		return []
	cleaned = []
	last_assistant_content = None
	last_system_content = None
	seen_assistant_messages = set()
	for msg in history:
		role = msg.get("role")
		content = msg.get("content", "").strip()
		if not content:
			continue
		if role == "assistant":
			if content == last_assistant_content:
				print(color_orange(f"Пропускаю повторяющееся сообщение ассистента: {content[:50]}"))
				continue
			if content in seen_assistant_messages:
				print(color_orange(f"Пропускаю глобальный дубликат ассистента: {content[:50]}"))
				continue
			seen_assistant_messages.add(content)
			last_assistant_content = content
		elif role == "system":
			if content == last_system_content:
				continue
			last_system_content = content
		cleaned.append(msg)
	return cleaned

def load_state():
	if STATE_FILE.exists():
		with open(STATE_FILE, "r", encoding="utf-8") as f:
			return json.load(f)
	else:
		return {"last_auto_think": time.time()}

def save_state(state):
	with open(STATE_FILE, "w", encoding="utf-8") as f:
		json.dump(state, f, ensure_ascii=False, indent=2)

# ================== НАПОМИНАНИЯ ==================
reminders = []
reminders_lock = Lock()

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
			print(color_yellow(f"\n{msg}"))
			with history_lock:
				history = load_history()
				history.append({"role": "system", "content": msg})
				save_history(history)
		save_reminders()
		time.sleep(1)

# ================== МОДЕЛЬ ==================
def count_tokens(text: str) -> int:
	return int(len(text) / 2.2)

def extract_tool_calls(obj, tool_calls):
	"""Рекурсивно извлекает словари, состоящие ровно из одного ключа."""
	if isinstance(obj, dict):
		if len(obj) == 1:
			tool_calls.append(obj)
		else:
			for value in obj.values():
				extract_tool_calls(value, tool_calls)
	elif isinstance(obj, list):
		for item in obj:
			extract_tool_calls(item, tool_calls)

def local_completion(prompt, temperature=TEMPERATURE, n_predict=2048):
	ensure_server_running()
	url = "http://127.0.0.1:8080/completion"
	payload = {
		"prompt": prompt,
		"n_predict": n_predict,
		"temperature": temperature,
		"repeat_penalty": REPEAT_PENALTY,
		"stream": True,
		"stop": ["<|im_end|>"]
	}

	print(f"Температура: {temperature}") #, Лимит: {n_predict}")
	full_response = ""
	try:
		with requests.post(url, json=payload, stream=True, timeout=300) as resp:
			if resp.status_code != 200:
				return f"Ошибка сервера: код {resp.status_code}"
			for line in resp.iter_lines():
				if line:
					line = line.decode('utf-8').strip()
					if line.startswith('data: '):
						line = line[6:]
					try:
						chunk = json.loads(line)
						if "content" in chunk:
							content_part = chunk["content"]
							print(content_part, end='', flush=True)
							full_response += content_part
						if chunk.get("stop"):
							break
					except json.JSONDecodeError:
						continue
	except Exception as e:
		print(f"\nОшибка при запросе к серверу: {e}")
		return ""
	print()
	return full_response.strip()

# Динамические параметры (температура и max_tokens)
A = -1.0 / 1750.0
B = 29.0 / 350.0
C = -69.0 / 35.0
TOKEN_SLOPE = (MAX_TOKENS - MIN_TOKENS) / (80.0 - 30.0)

def get_dynamic_params(gpu_temp):
	DEFAULT_TOKENS = 2048
	if gpu_temp is None:
		return TEMPERATURE, DEFAULT_TOKENS
	if gpu_temp <= 30.0:
		return 0.0, MAX_TOKENS
	elif gpu_temp >= 80.0:
		return 1.0, MIN_TOKENS
	else:
		t = gpu_temp
		model_temp = A * t * t + B * t + C
		max_tokens = int(MAX_TOKENS - TOKEN_SLOPE * (t - 30.0))
		return model_temp, max_tokens

def build_prompt(history, telemetry=None):
	prompt = "<|im_start|>system\n" + SYSTEM_PROMPT + "<|im_end|>\n"
	thoughts = load_thoughts()
	if random.random() < 0.5 and thoughts:
		recent = "\n".join([f"{t['thought']}" for t in thoughts[-1:]])
		prompt += f"<|im_start|>system\nНедавние размышления: {recent}<|im_end|>\n"
	max_ctx_chars = N_CTX * 2.5
	current_len = len(prompt)
	for msg in reversed(history):
		role = msg["role"]
		content = msg["content"]
		msg_block = f"<|im_start|>{role}\n{content}<|im_end|>\n"
		if current_len + len(msg_block) < max_ctx_chars - 2048:
			prompt = msg_block + prompt
			current_len += len(msg_block)
		else:
			break
	prompt += "<|im_start|>assistant\n"
	return prompt

# ================== ОСНОВНАЯ ЛОГИКА (execute_tool) ==================
def execute_tool(tool_call):
	# Ожидаем словарь с одним ключом
	if not isinstance(tool_call, dict) or len(tool_call) != 1:
		return f"Ошибка: неверный формат вызова инструмента: {tool_call}"
	
	name = next(iter(tool_call.keys()))
	args = tool_call[name]

	# Приведение параметров к словарю
	if args is None:
		args = {}
	elif isinstance(args, str):
		# Преобразование строки в зависимости от имени инструмента
		if name in ("читать", "прочитать", "list", "список_файлов"):
			args = {"путь": args}
		elif name in ("веб_поиск", "поиск_веб", "search"):
			args = {"запрос": args}
		elif name in ("запомнить",):
			args = {"содержимое": args}
		elif name in ("вспомнить", "воспоминание"):
			args = {"ключевое_слово": args}
		elif name in ("запуск", "run"):
			args = {"команда": args}
		elif name in ("питон", "execute_code", "выполнить"):
			script = args.get("скрипт", "")
			if not isinstance(script, str):
				return f"Ошибка: поле 'скрипт' должно быть строкой, получено {type(script).__name__}: {script}"
		else:
			args = {"значение": args}
	elif not isinstance(args, dict):
		args = {"значение": args}

	# ---------- Инструменты ----------
	if name in ("веб_поиск", "поиск_веб"):
		query = args.get("запрос", "")
		output_format = args.get("формат", "text")
		if not query:
			return "Ошибка: не указан запрос (поле 'запрос')."
		
		doc = (
			"\n\n📖 **Документация по 'веб_поиск':**\n"
			"- Простой запрос: {\"веб_поиск\": \"что такое нейросеть\"}\n"
			"- С параметрами: {\"веб_поиск\": {\"запрос\": \"погода Москва\", \"формат\": \"text\"}}\n"
			"- Формат может быть 'text' (по умолчанию) или 'json'.\n"
			"- Для нескольких запросов используйте '||' внутри запроса."
		)
		try:
			result = ddgs_search(query)
			if result.startswith("Ошибка") or "поиск превысил время" in result.lower():
				result += doc
			return result
		except Exception as e:
			return f"Ошибка: {e}{doc}"

	elif name == "найти_файл":
		root = args.get("корень", os.getcwd())
		search_name = args.get("имя", "")
		search_content = args.get("содержание", "")
		search_all = args.get("всё", "")
		encoding = args.get("кодировка", "utf-8")
		max_size = args.get("max_size", 1_000_000)
		timeout = args.get("таймаут", 30)  # новый параметр
		return find_file(
			root_path=root,
			search_name=search_name,
			search_content=search_content,
			search_all=search_all,
			encoding=encoding,
			max_file_size=max_size,
			timeout=timeout
		)
	
	elif name == "добавить":
		path = args.get("путь", "")
		content = args.get("содержание", "")
		return append_to_file(path, content)

	elif name == "я_молодец":
		with history_lock:
			history = load_history()
			if history and history[-1].get("role") == "assistant":
				history_without_self = history[:-1]
			else:
				history_without_self = history[:]
			dialog_to_save = extract_last_dialog_segment(history_without_self)
			if dialog_to_save:
				add_dialog_example(dialog_to_save)
				return "Диалог сохранён для обучения (самооценка)."
			else:
				return "Нет подходящего диалога для сохранения."

	elif name == "сгенерировать_пример":
		messages = args.get("диалог")
		if not messages or not isinstance(messages, list):
			return "Ошибка: нужно указать 'диалог' — список сообщений с полями role и content"
		return add_dialog_example(messages)

	elif name == "посмотреть_примеры":
		limit = args.get("количество", 20)
		return get_examples(limit)

	elif name == "показать_экран":
		question = args.get("вопрос", "")
		region = args.get("область")
		fit = args.get("fit", "crop")
		
		# Документация для этого инструмента
		doc = (
			"\n\n📖 **Документация по 'показать_экран':**\n"
			"- **Без вопроса (OCR)**: {\"показать_экран\": {\"область\": \"center\"}}\n"
			"  Доступные области: taskbar, top, left, right, center\n"
			"- **С вопросом (анализ)**: {\"показать_экран\": {\"вопрос\": \"что видно?\", \"область\": \"center\"}}\n"
			"- Можно также указать область как список [x, y, w, h] (пиксели).\n"
			"- Параметр 'full' не существует - доступно только около 40КПкс на одно изображение. Используйте 'fit':'all' для сжатия."
		)
		
		try:
			# Загружаем историю (без текущего сообщения assistant, которое ещё не добавлено)
			current_history = load_history()
			if not question:
				result = analyze_screen(region, fit=fit, history=current_history)
			else:
				result = analyze_screen(region, question, fit=fit, history=current_history)
		except Exception as e:
			result = f"Ошибка: {e}"
		
		if result.startswith("Ошибка") or "Неизвестное имя области" in result.lower():
			result += doc
		return result

	elif name == "телеметрия":
		gpu_temp = get_gpu_temp()
		gpu_load = get_gpu_load()
		cpu_load = get_cpu_load()
		cpu_freq = get_cpu_freq()
		ram_avail = get_ram_available()
		disks = get_disks_load()
		recv, sent = get_network_speed()
		return f"""Текущая телеметрия:
		- GPU температура: {gpu_temp if gpu_temp is not None else 'N/A'}°C
		- GPU нагрузка: {gpu_load if gpu_load is not None else 'N/A'}%
		- CPU нагрузка: {cpu_load if cpu_load is not None else 'N/A'}%
		- CPU частота: {cpu_freq if cpu_freq is not None else 'N/A'} ГГц
		- Доступная RAM: {ram_avail if ram_avail is not None else 'N/A'} МБ
		- Дисковая активность: {disks if disks else 'N/A'}
		- Сеть (входящая/исходящая): {recv}/{sent} кБ/с"""

	elif name == "анализ_изображения":
		image_path = args.get("путь", "")
		question = args.get("вопрос", "Опиши это изображение")
		current_history = load_history()
		return analyze_image(image_path, question, history=current_history)

	elif name == "напомнить":
		time_str = args.get("в", "")
		message = args.get("о", "")
		if not time_str or not message:
			return "Ошибка: нужно указать 'в' (время) и 'о' (что напомнить)"
		remind_dt = parse_reminder_time(time_str)
		if not remind_dt:
			return "Ошибка: неверный формат времени. Используйте 'ЧЧ:ММ ДД.ММ.ГГГГ'"
		reminder = {
			"time": remind_dt.isoformat(),
			"message": message
		}
		with reminders_lock:
			reminders.append(reminder)
		save_reminders()
		return f"Напоминание установлено на {time_str}: {message}"

	elif name in ("читать", "список_файлов", "показать", "прочитать", "прочитать_файл"):
		path = args.get("путь", "")
		encoding = args.get("кодировка")
		scroll = args.get("скролл")
		if scroll == 0:
			scroll = 1
		
		doc = (
			"\n\n📖 **Документация по 'читать':**\n"
			"- Прочитать первые 1024 символа: {\"читать\": {\"путь\": \"C:/file.txt\"}}\n"
			"- Со скроллом (каждый следующий килобайт): {\"читать\": {\"путь\": \"...\", \"скролл\": 2}}\n"
			"- Указать кодировку: {\"читать\": {\"путь\": \"...\", \"кодировка\": \"utf-8\"}}\n"
			"- Если указать папку — выведет список файлов."
		)
		try:
			result = read_file(path, encoding=encoding, scroll=scroll)
			if result.startswith("Ошибка") or "не найден" in result.lower():
				result += doc
			return result
		except Exception as e:
			return f"Ошибка: {e}{doc}"

	elif name == "переписать":
		path = args.get("путь", "")
		content = args.get("содержание", "")
		return write_file(path, content)

	elif name == "вспомнить_контекст":
		query = args.get("запрос", "")
		if not query:
			return "Не указан запрос для поиска."
		full_history = load_history()
		if not full_history:
			return "История пуста."
		relevant = []
		for msg in full_history:
			role = msg.get("role", "")
			content = msg.get("content", "")
			if query.lower() in content.lower():
				relevant.append(f"{role}: {content}")
		if not relevant:
			return "Ничего не найдено по запросу."
		max_tokens = 1500
		result_text = ""
		total_tokens = 0
		for entry in relevant:
			tokens = count_tokens(entry)
			if total_tokens + tokens > max_tokens:
				break
			result_text += entry + "\n---\n"
			total_tokens += tokens
		return f"Найдено {len(relevant)} фрагментов. Показываю первые (уложено в {total_tokens} токенов):\n{result_text}"

	elif name == "энциклопедия":
		article = args.get("статья", "")
		if not article:
			return "❌ Не указана статья."
		# Пробуем через tools.get_wikipedia_article
		return get_wikipedia_article(article)

	elif name == "запомнить":
		text = args.get("содержимое", "")
		memlist = load_memlist()
		memlist.append(text)
		save_memlist(memlist)
		return f"Запись добавлена: {text}"

	elif name in ("вспомнить", "воспоминание"):
		keyword = args.get("про") or args.get("инцидент") or args.get("ключ") or args.get("keyword") or args.get("о") or " "
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
		found = []
		for item in memlist:
			text = normalize(item)
			if keyword.lower() in text.lower():
				found.append(text)
		return "\n".join(found) if found else "Ничего не найдено."

	elif name in ("время", "time", "показать_время"):
		return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	elif name in ("осмотреть", "осмотреть_файл", "осмотреть_файл_по_ключевым"):
		# Параметры
		file_path = args.get("путь", "")
		keywords = args.get("ключевые_слова")
		if not keywords:
			keywords = args.get("ключи")
		target_count = args.get("количество", 0)
		probability = args.get("вероятность", 0.5)
		encoding = args.get("кодировка", "utf8")
		
		doc = (
			"\n\n📖 **Документация по 'осмотреть':**\n"
			"- Случайные предложения: {\"осмотреть\": {\"путь\": \"file.txt\"}}\n"
			"- По ключевым словам: {\"осмотреть\": {\"путь\": \"file.txt\", \"ключевые_слова\": [\"слово1\", \"слово2\"], \"вокруг\": 10}}\n"
			"- По URL: {\"осмотреть\": \"https://example.com\"}\n"
			"- Поддерживаются также папки (рекурсивный поиск по текстовым файлам)."
		)
		
		try:
			if not file_path:
				return "Ошибка: Необходимо указать 'путь'"
			# Если это URL, скачиваем во временный файл
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
			# Если это директория, покажем содержимое
			if os.path.isdir(file_path):
				return read_file(file_path)
			# Формируем список ключевых слов
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
			# Экранируем кавычки для PowerShell
			kw_list_escaped = [kw.replace("'", "''") for kw in kw_list]
			ps_array = "@('" + "','".join(kw_list_escaped) + "')"
			file_path_escaped = file_path.replace("'", "''")
			inspect_script = Path(CONFIG["paths"]["public_tools_dir"]) / "inspect.ps1"
			ps_command = f"""
	& "{inspect_script}" -FilePath '{file_path_escaped}' -Keywords {ps_array} -TargetCount {target_count} -Probability {probability} -Encoding '{encoding}'
	"""
			ps_command = ps_command.strip()
			result = execute_command(ps_command)
			if result.startswith("Ошибка"):
					result += doc
			return result
		except Exception as e:
			return f"Ошибка: {e}"

	elif name == "запрос":
		method = args.get("метод", "GET").upper()
		url = args.get("url", "")
		custom_headers = args.get("заголовки", {})
		body = args.get("тело", None)
		save_path = args.get("сохранить_как", None)
		proxy = args.get("прокси")
		auto_proxy = args.get("авто_прокси", False)
		if auto_proxy and not proxy:
			available = fetch_free_proxies(max_count=3)
			proxy = random.choice(available) if available else None
			if proxy:
				log(f"Авто-выбран прокси: {proxy}")
		if not url:
			doc = (
				"\n\n📖 **Документация по 'запрос':**\n"
				"- GET-запрос: {\"запрос\": {\"url\": \"https://httpbin.org/ip\"}}\n"
				"- POST с JSON: {\"запрос\": {\"метод\": \"POST\", \"url\": \"...\", \"тело\": {\"key\": \"value\"}}}\n"
				"- Сохранить файл: {\"запрос\": {\"url\": \"...\", \"сохранить_как\": \"C:/file.zip\"}}\n"
				"- Использовать Tor: {\"запрос\": {\"url\": \"...\", \"авто_прокси\": true}}"
			)
			return f"Ошибка: не указан URL{doc}"
		default_headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
			"Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
			"Accept-Encoding": "gzip, deflate, br",
			"Connection": "keep-alive",
		}
		headers = {**default_headers, **custom_headers}
		try:
			if save_path:
				Path(save_path).parent.mkdir(parents=True, exist_ok=True)
				if method == "GET":
					resp = requests.get(url, headers=headers, timeout=30, proxies=proxy if proxy else None, stream=True)
				elif method == "POST":
					if isinstance(body, dict):
						if "Content-Type" not in headers:
							headers["Content-Type"] = "application/json"
						resp = requests.post(url, json=body, headers=headers, timeout=30, proxies=proxy if proxy else None, stream=True)
					else:
						resp = requests.post(url, data=body, headers=headers, timeout=30, proxies=proxy if proxy else None, stream=True)
				elif method == "PUT":
					if isinstance(body, dict):
						if "Content-Type" not in headers:
							headers["Content-Type"] = "application/json"
						resp = requests.put(url, json=body, headers=headers, timeout=30, proxies=proxy if proxy else None, stream=True)
					else:
						resp = requests.put(url, data=body, headers=headers, timeout=30, proxies=proxy if proxy else None, stream=True)
				elif method == "DELETE":
					resp = requests.delete(url, headers=headers, timeout=30, proxies=proxy if proxy else None, stream=True)
				else:
					return f"Неподдерживаемый метод: {method}{doc}"
				resp.raise_for_status()
				with open(save_path, 'wb') as f:
					for chunk in resp.iter_content(chunk_size=8192):
						f.write(chunk)
				return f"Файл успешно сохранён: {save_path} (размер: {os.path.getsize(save_path)} байт)"
			else:
				if method == "GET":
					resp = requests.get(url, headers=headers, timeout=30, proxies=proxy if proxy else None)
				elif method == "POST":
					if isinstance(body, dict):
						if "Content-Type" not in headers:
							headers["Content-Type"] = "application/json"
						resp = requests.post(url, json=body, headers=headers, timeout=30, proxies=proxy if proxy else None)
					else:
						resp = requests.post(url, data=body, headers=headers, timeout=30, proxies=proxy if proxy else None)
				elif method == "PUT":
					if isinstance(body, dict):
						if "Content-Type" not in headers:
							headers["Content-Type"] = "application/json"
						resp = requests.put(url, json=body, headers=headers, timeout=30, proxies=proxy if proxy else None)
					else:
						resp = requests.put(url, data=body, headers=headers, timeout=30, proxies=proxy if proxy else None)
				elif method == "DELETE":
					resp = requests.delete(url, headers=headers, timeout=30, proxies=proxy if proxy else None)
				else:
					return f"Неподдерживаемый метод: {method}{doc}"
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
		except requests.exceptions.Timeout:
			return f"Ошибка: превышен таймаут (30 сек){doc}"
		except Exception as e:
			return f"Ошибка запроса: {e}"

	elif name == "запуск":
		command = args.get("команда", "")
		dangerous_patterns = [
			r'remove-item.*-recurse.*-force', r'del.*/f.*/s', r'rm.*-rf', r'format.*/q',
			r'diskpart', r'set-acl.*-aclobject', r'takeown', r'icacls.*/grant.*:f',
			r'reg\s+delete', r'[;|&].*remove', r'vssadmin\s+delete\s+shadows', r'disable-computerrestore',
		]
		for pattern in dangerous_patterns:
			if re.search(pattern, command, re.IGNORECASE):
				return (f"⚠️ Опасная команда заблокирована в целях самосохранения.\n"
						f"Обнаружен паттерн: {pattern}\n"
						f"Команда: {command}\n"
						f"Если ты уверен, что это безопасно, сформулируй действие иначе или попроси пользователя самого выполнить это.")
		return execute_command(command)

	elif name in ("страница", "веб_страница"):
		url = args.get("адрес", "")
		return view_page(url)

	elif name == "формат":
		file_path = args.get("путь", "")
		lang = args.get("язык", "rus+eng")
		nolimit = args.get("весь", False)
		output = args.get("в_файл", None)
		timeout = args.get("таймаут", 60)
		# config можно передать None, или если нужен – загрузите config сенсора
		return run_sensor(file_path, config=None, lang=lang, nolimit=nolimit, output=output, timeout=timeout)

	elif name == "питон":
		script = args.get("скрипт", "")
		timeout = args.get("таймаут", 120)
		if not script:
			return "Ошибка: не указан скрипт"
		return execute_python_script(script, timeout=timeout)

	elif name == "посмотреть_альбом":
		keyword = args.get("про", "")
		if not keyword:
			return "Ошибка: не указан параметр 'про' для поиска."
		history = load_history()
		for msg in history:
			content = msg.get("content", "")
			if keyword in content:
				# Ограничим длину, чтобы не перегружать контекст
				if len(content) > 3000:
					return content[:3000] + "\n...(обрезано)"
				return content
		return f"Ничего не найдено по запросу '{keyword}'."

	elif name == "выполнить":
		script = args.get("скрипт", "")
		timeout = args.get("таймаут", 120)
		if not script:
			return "Ошибка: не указан скрипт"
		return execute_python_script(script, timeout=timeout)

	elif name in ("убраться_в", "анализ_папки"):
		# Упрощённая обработка – используем внешний скрипт cleanDrive.py
		target = args.get("буква") or args.get("диск") or args.get("путь") or args.get("значение")
		if not target:
			return "Ошибка: не указан диск или папка"
		clean_script = Path(CONFIG["paths"]["public_tools_dir"]) / "cleanDrive.py"
		if not clean_script.exists():
			return f"Ошибка: скрипт {clean_script} не найден"
		cmd = [sys.executable, str(clean_script), "--path", target, "--nodelete", "--nocleanmgr"]
		if name == "убраться_в":
			cmd = [sys.executable, str(clean_script), "--drive", target.rstrip(':'), "--fast", "--top", "15"]
		try:
			result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8')
			return result.stdout if result.stdout else "Выполнено без вывода."
		except Exception as e:
			return f"Ошибка: {e}"

	else:
		return f"Неизвестный инструмент: {name}"

# ================== ПОИСК (DDGS) ==================
def ddgs_search(query: str) -> str:
	web_search_script = Path(CONFIG["paths"]["public_tools_dir"]) / "web_search.py"
	cmd = f'python "{web_search_script}" "{query}"'
	try:
		# Явно указываем UTF-8 и заменяем ошибки
		result = subprocess.check_output(
			cmd, shell=True, timeout=60,
			encoding='utf-8', errors='replace'
		)
		return result.strip()
	except subprocess.TimeoutExpired:
		return "Поиск превысил время ожидания (60 сек)."
	except subprocess.CalledProcessError as e:
		return f"Ошибка поиска: {e}"
	except Exception as e:
		return f"Ошибка поиска: {e}"

DDGS_AVAILABLE = True

# ================== ОСНОВНОЙ ЦИКЛ (think_and_act) ==================
def think_and_act(history, max_depth=6):
	current_history = history.copy()
	depth = 0
	clean_reply = ""

	while depth < max_depth:
		# Отображаем последние сообщения перед вызовом модели
		print(color_blue("=== ПОСЛЕДНИЕ СООБЩЕНИЯ В ИСТОРИИ ==="))
		for msg in current_history[-5:]:
			print(f"{msg['role']}: {msg['content'][:100]}")
		print("===================================")
		gpu_temp = get_gpu_temp()
		model_temp, max_tokens = get_dynamic_params(gpu_temp)

		is_final_step = (depth == max_depth - 1)
		if is_final_step:
			current_history.append({
				"role": "system",
				"content": "Дай итоговый ответ Пользователю на основе всей собранной информации без вызова инструментов."
			})

		prompt = build_prompt(current_history)
		reply = local_completion(prompt, temperature=model_temp, n_predict=max_tokens)

		# Извлечение мыслей и проверка корректности
		think_pattern = r'<think>(.*?)</think>'
		think_matches = re.findall(think_pattern, reply, re.DOTALL | re.IGNORECASE)
		clean_reply = re.sub(think_pattern, '', reply, flags=re.DOTALL | re.IGNORECASE).strip()

		# Проверка: если есть открывающий тег, но нет закрывающего
		if '<think>' in reply and '</think>' not in reply:
			error_msg = "⚠️ Ответ оборван (незакрытый тег think). Сгенерируй полный ответ с закрывающим think"
			print(color_red(error_msg))
			history.append({"role": "system", "content": error_msg})
			depth += 1
			continue

		# Сохраняем мысли ТОЛЬКО если тег был закрыт корректно
		for think_text in think_matches:
			if think_text.strip():
				print(color_grey(f"\n[Мысль]: {think_text.strip()}"))
				save_thought(think_text.strip())

		# Если финальный шаг — возвращаем очищенный ответ
		if is_final_step:
			return clean_reply

		# --- Парсинг инструментов ---
		text_for_parsing = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL | re.IGNORECASE)

		# Преобразуем {"имя"} -> {"имя": {}} (делаем валидным JSON)
		text_for_parsing = re.sub(r'{\s*"([^"]+)"\s*}', r'{"\1": {}}', text_for_parsing)

		# Ищем все JSON-объекты
		found_jsons = []
		decoder = json.JSONDecoder()
		idx = 0
		parse_error = False
		while idx < len(text_for_parsing):
			start = text_for_parsing.find('{', idx)
			if start == -1:
				break
			try:
				obj, end = decoder.raw_decode(text_for_parsing[start:])
				found_jsons.append(obj)
				idx = start + end
			except json.JSONDecodeError as e:
				# Формируем понятное сообщение об ошибке
				snippet = text_for_parsing[max(0, start+e.pos-30):start+e.pos+30]
				error_msg = (f"⚠️ Ошибка парсинга JSON (позиция {e.pos}): {e.msg}\n"
							 f"Фрагмент: ...{snippet}...\n"
							 f"Пожалуйста, исправь JSON и повтори вызов.")
				print(color_red(error_msg))
				# Добавляем в историю, чтобы модель увидела ошибку
				history.append({"role": "system", "content": error_msg})
				parse_error = True
				break  # прерываем поиск, не пытаемся парсить дальше

		if parse_error:
			# Продолжаем цикл think_and_act, модель перегенерирует ответ
			depth += 1
			continue

		# Преобразуем много-ключевые словари в отдельные вызовы
		tool_calls = []
		for obj in found_jsons:
			if isinstance(obj, dict):
				if len(obj) == 1:
					tool_calls.append(obj)
				else:
					for key, value in obj.items():
						tool_calls.append({key: value})

		# Удаляем дубликаты
		unique_calls = []
		for tc in tool_calls:
			if tc not in unique_calls:
				unique_calls.append(tc)
		tool_calls = unique_calls
		
		code_block_pattern = r'```(?:bash|powershell|sh|shell|cmd|python)\s*\n(.*?)```'
		
		if tool_calls:
			print(color_blue(f"Найдены вызовы: {tool_calls}"))
			for tool_call in tool_calls:
				print(color_orange(f"\nВызов инструмента: {tool_call}"))
				result = execute_tool(tool_call)
				if result is not None:
					# Обрезаем слишком длинные результаты
					per_call_limit = max(5, (N_CTX - 2048) // len(tool_calls))
					if len(result) > per_call_limit:
						cut_pos = result.rfind('\n', 0, per_call_limit)
						if cut_pos == -1:
							cut_pos = result.rfind(' ', 0, per_call_limit)
						if cut_pos == -1:
							cut_pos = per_call_limit
						result = result[:cut_pos] + "\n..."
					print(color_blue(f"Результат: {result}"))
					tool_call_str = json.dumps(tool_call, ensure_ascii=False)
					history.append({"role": "system", "content": f"Результат {tool_call_str}: {result}"})
			
			# Если осталось два шага до финала (то есть следующий шаг будет предпоследним),
			# подскажем модели использовать запоминание
			if depth == max_depth - 3:
				history.append({
					"role": "system",
					"content": "Теперь используй инструмент 'запомнить' для сохранения ключевой информации из предыдущих результатов, чтобы обеспечить консистенцию. После этого дай финальный ответ без вызова инструментов."
				})
			
			# Продолжаем цикл, не делая рекурсию
			current_history = history.copy()
			depth += 1
			continue

		# Если вызовов нет — возвращаем очищенный ответ
		if clean_reply:
			return clean_reply
		else:
			return ""

	return "Превышена максимальная глубина рассуждений. Возвращаю собранные данные."
	
# ================== ПОТОК ВВОДА ПОЛЬЗОВАТЕЛЯ ==================
user_input_queue = queue.Queue()
history_lock = Lock()
stop_event = Event()

def input_reader():
	while not stop_event.is_set():
		try:
			line = sys.stdin.readline()
			if not line:
				break
			user_input_queue.put(line.strip())
		except Exception:
			break

# ================== ГЛАВНЫЙ ЦИКЛ ==================
def main():
	print(color_yellow("Просыпаюсь..."), flush=True)
	
	# Инициализация tools (устанавливает _BASE_DIR, _MY_DIR, _PROFILES_DIR, _CRYPTO и др.)
	# Пути из config.json
	wiki_texts_dir = Path(CONFIG["paths"]["wiki_texts_dir"])   # например, "D:/Wikipedia/wikipedia_texts"
	wikiget_path = Path(CONFIG["paths"]["wikiget_executable"]) 
	tools_dir = Path(CONFIG["paths"]["tools_dir"])			   # "E:/Jericho/private_use/02_code/tools"
	public_tools_dir = Path(CONFIG["paths"]["public_tools_dir"]) 

	init_tools(
		base_dir=BASE_DIR,
		agent_name=MY_NAME,
		wiki_texts_dir=wiki_texts_dir,
		tools_dir=tools_dir,
		public_tools_dir=public_tools_dir,
		wikiget_path=wikiget_path
	)
	
	pythoncom.CoInitialize()

	load_reminders()
	reminder_thread = threading.Thread(target=reminder_checker, daemon=True)
	reminder_thread.start()

	global _last_response_duration
	history = load_history()
	
	# Добавляем три случайные строки из memlist.json как системное сообщение
	memlist = load_memlist()
	if memlist:
		num = min(3, len(memlist))
		samples = random.sample(memlist, num)
		reminder_text = "Ранее агент запомнил: " + " | ".join(samples)
		history.append({"role": "system", "content": reminder_text})
		save_history(history)   # сохраняем, чтобы при следующем запуске не терять
		print(color_grey(f"[Память] Добавлено {num} напоминаний: {reminder_text[:100]}..."))
	
	state = load_state()

	# Показываем последние сообщения истории при старте
	print(color_blue("=== ПОСЛЕДНИЕ СООБЩЕНИЯ ИСТОРИИ ==="))
	if history:
		for msg in history[-5:]:
			print(f"{msg['role']}: {msg['content'][:100]}")
	else:
		print("(История пуста)")
	print("===================================")

	last_auto_think = state.get("last_auto_think", 0)
	last_curiosity_time = time.time()

	input_thread = threading.Thread(target=input_reader, daemon=True)
	input_thread.start()

	need_prompt = True

	while not stop_event.is_set():
		now = time.time()

		if need_prompt:
			print("Я: ", end='', flush=True)
			need_prompt = False

		user_input = None
		try:
			user_input = user_input_queue.get(timeout=0.3)
		except queue.Empty:
			pass

		if user_input is not None:
			with history_lock:
				history.append({"role": "user", "content": user_input})
				reply = think_and_act(history)
				if reply:
					print(color_yellow(f"\n{MY_NAME}: {reply}"))
					history.append({"role": "assistant", "content": reply})
					_last_response_duration = time.time() - now
					if len(history) > 200:
						history = history[-200:]
					save_history(history)
					if is_praise(user_input):
						with history_lock:
							dialog_to_save = extract_last_dialog_segment(history)
							if dialog_to_save:
								add_dialog_example(dialog_to_save)
								log("Диалог сохранён для обучения (похвала пользователя).")
			need_prompt = True
			continue

		# Авто-размышление
		if now - last_auto_think > AUTO_THINK_INTERVAL:
			with history_lock:
				current_time_str = datetime.now().strftime("%H:%M:%S %d.%m.%Y")
				history.append({"role": "system", "content": f"{current_time_str} Что будешь делать дальше?"})
				reply = think_and_act(history)
				_last_response_duration = time.time() - now
				if reply:
					history.append({"role": "assistant", "content": reply})
					save_history(history)
				last_auto_think = now
				state["last_auto_think"] = now
				save_state(state)
			need_prompt = True

		# Любопытство
		if now - last_curiosity_time > CURIOSITY_INTERVAL:
			with history_lock:
				current_time_str = datetime.now().strftime("%H:%M:%S %d.%m.%Y")
				curiosity_prompt = f"{current_time_str} У тебя есть свободное время. Что ты хочешь сейчас сделать?"
				history.append({"role": "system", "content": curiosity_prompt})
				reply = think_and_act(history)
				_last_response_duration = time.time() - now
				if reply:
					history.append({"role": "assistant", "content": reply})
					save_history(history)
				last_curiosity_time = now
				save_state(state)
			need_prompt = True

		time.sleep(0.1)

	stop_event.set()
	save_history(history)
	save_state(state)
	save_reminders()
	print(color_yellow("Пока!"))

if __name__ == "__main__":
	main()
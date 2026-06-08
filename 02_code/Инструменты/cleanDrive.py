# cleanDrive.py — универсальная очистка для C/D/E/...
import os
import time
import json
import subprocess
import argparse
import threading
import shutil
from pathlib import Path
import sys
import concurrent.futures

SKIP_SYSTEM_DIRS = {
	'Windows', 'System Volume Information', '$Recycle.Bin', 'Recovery', 'Boot', 'Wikipedia'
}

def get_size_with_timeout(path, timeout_sec=5):
	"""
	Вычисляет размер path с таймаутом.
	Возвращает tuple: (размер_в_байтах, был_ли_таймаут)
	При таймауте возвращает размер, который успели насчитать за timeout_sec секунд.
	"""
	total = 0
	done = threading.Event()
	timeout_occurred = False

	def worker():
		nonlocal total
		try:
			if path.is_file():
				try:
					total = path.stat().st_size
				except OSError:
					total = 0
			elif path.is_dir():
				for entry in path.rglob('*'):
					if entry.is_file():
						try:
							total += entry.stat().st_size
						except OSError:
							pass
					# Если время истекло – выходим (но поток всё равно daemon)
					if done.is_set():
						return
		except Exception:
			pass
		finally:
			done.set()

	thread = threading.Thread(target=worker, daemon=True)
	thread.start()
	finished = done.wait(timeout_sec)
	if not finished:
		timeout_occurred = True
		# Поток продолжит работу в фоне, но мы его не дожидаемся
	return total, timeout_occurred
	
def get_size_of_path_with_progress(path, progress_callback=None):
	total = 0
	if path.is_file():
		try:
			total = path.stat().st_size
		except OSError:
			pass
		if progress_callback:
			progress_callback(1)
	elif path.is_dir():
		for entry in path.rglob('*'):
			if entry.is_file():
				try:
					total += entry.stat().st_size
				except OSError:
					pass
			if progress_callback:
				progress_callback(1)
	return total
	
def clean_temp_directory(temp_path, max_age_days=7):
	total_freed = 0
	deleted_files = []
	errors = []
	exclude_dirs = {'Cookies', 'History', 'WebCache', 'Microsoft', 'Edge', 'Google', 'Packages'}
	if not os.path.exists(temp_path):
		return 0, [], [f"Путь не существует: {temp_path}"]
	current_time = time.time()
	max_age_seconds = max_age_days * 24 * 60 * 60
	for root, dirs, files in os.walk(temp_path, topdown=True):
		dirs[:] = [d for d in dirs if d not in exclude_dirs]
		for file in files:
			file_path = os.path.join(root, file)
			try:
				file_stat = os.stat(file_path)
				file_age = current_time - max(file_stat.st_atime, file_stat.st_mtime)
				if file_age > max_age_seconds:
					file_size = file_stat.st_size
					os.remove(file_path)
					total_freed += file_size
					deleted_files.append({
						'file': file_path,
						'size_mb': round(file_size / (1024*1024), 2),
						'age_days': round(file_age / (24*60*60), 1)
					})
			except (PermissionError, OSError) as e:
				errors.append(f"Ошибка удаления {file_path}: {e}")
				continue
	return total_freed, deleted_files, errors

def run_disk_cleanup():
	print("\n=== ЗАПУСК ОЧИСТКИ ДИСКА (cleanmgr) ===", flush=True)
	try:
		usage_before = shutil.disk_usage("C:")
		free_before_gb = usage_before.free / (1024**3)
		print(f"Свободно на диске C: до очистки: {free_before_gb:.2f} ГБ", flush=True)
		print("Выполняется cleanmgr /sagerun:1 ... (может занять несколько минут)", flush=True)
		subprocess.run(["cleanmgr", "/sagerun:1"], check=True, capture_output=True, text=True)
		usage_after = shutil.disk_usage("C:")
		free_after_gb = usage_after.free / (1024**3)
		freed_gb = free_after_gb - free_before_gb
		print(f"Свободно на диске C: после очистки: {free_after_gb:.2f} ГБ", flush=True)
		print(f"✅ Очистка диска завершена. Освобождено примерно: {freed_gb:.2f} ГБ", flush=True)
		return True
	except subprocess.CalledProcessError as e:
		print(f"❌ Ошибка при запуске cleanmgr: {e}", flush=True)
		return False
	except Exception as e:
		print(f"❌ Не удалось выполнить очистку: {e}", flush=True)
		return False

def get_size_of_path(path):
	total = 0
	if path.is_file():
		try:
			total = path.stat().st_size
		except OSError:
			pass
	elif path.is_dir():
		for entry in path.rglob('*'):
			if entry.is_file():
				try:
					total += entry.stat().st_size
				except OSError:
					continue
	return total

def get_top_downloads_objects(n=10):
	downloads_path = Path.home() / "Downloads"
	if not downloads_path.exists():
		return []
	objects_with_size = []
	for item in downloads_path.iterdir():
		size = get_size_of_path(item)
		if size > 0:
			objects_with_size.append({
				"name": item.name,
				"path": str(item),
				"size_mb": round(size / (1024*1024), 2),
				"is_dir": item.is_dir()
			})
	objects_with_size.sort(key=lambda x: x['size_mb'], reverse=True)
	return objects_with_size[:n]

def analyze_folder(folder_path, top=15, fast=True):
	folder = Path(folder_path)
	if not folder.exists() or not folder.is_dir():
		print(f"❌ Папка не существует: {folder_path}")
		return

	if not fast:
		run_treesize(target_path=str(folder), top_level=10, drill_depth=1)
		return

	print(f"\n=== АНАЛИЗ ПАПКИ: {folder} ===")
	items = list(folder.iterdir())
	total = len(items)
	results = []

	for i, item in enumerate(items, 1):
		print(f"[{i}/{total}] {item.name[:60]}", file=sys.stderr, flush=True)

		size, timeout = get_size_with_timeout(item, timeout_sec=5)
		if timeout:
			print(f"{item.name} > {size/(1024**3):.1f} ГБ", file=sys.stderr)
		if size > 0:
			results.append({
				"name": item.name,
				"path": str(item),
				"size_mb": round(size / (1024*1024), 2),
				"is_dir": item.is_dir()
			})

	results.sort(key=lambda x: x['size_mb'], reverse=True)
	top_items = results[:top]
	total_size = sum(it['size_mb'] for it in top_items)

	print(f"\nТоп-{len(top_items)} объектов в папке (по занимаемому месту):")
	for i, it in enumerate(top_items, 1):
		type_label = "[ПАПКА]" if it['is_dir'] else "[ФАЙЛ] "
		print(f"  {i:2}. {type_label} {it['name'][:50]:<50} {it['size_mb']:>8.2f} МБ")
	print(f"\nСуммарный размер этих объектов: {total_size:.2f} МБ ({total_size/1024:.2f} ГБ)")

def print_top_downloads():
	print("\n=== ТОП-10 ОБЪЕКТОВ В ПАПКЕ 'C:\\Downloads' (файлы и папки) ===", flush=True)
	top_objects = get_top_downloads_objects(10)
	if not top_objects:
		print("Папка Downloads пуста или не найдена.", flush=True)
		return
	total_size = sum(item['size_mb'] for item in top_objects)
	print(f"Общий размер этих 10 объектов: {total_size:.2f} МБ ({total_size/1024:.2f} ГБ)", flush=True)
	print("Список:")
	for i, item in enumerate(top_objects, 1):
		type_label = "[ПАПКА]" if item['is_dir'] else "[ФАЙЛ] "
		print(f"  {i:2}. {type_label} {item['name']:<47} {item['size_mb']:>8.2f} МБ")
	print("\n💡 Рекомендуется удалить ненужные крупные папки/файлы вручную или переместить на другой диск.\nЗапустить автоматическую очистку диска Windows (cleanmgr /sagerun:1)? [y/N]", flush=True)

def run_treesize(drive_letter=None, target_path=None, top_level=10, drill_depth=1):
	script_dir = os.path.dirname(os.path.abspath(__file__))
	treesize_script = os.path.join(script_dir, "TreeSize.ps1")
	if not os.path.exists(treesize_script):
		print(f"\n⚠️ Скрипт TreeSize.ps1 не найден: {treesize_script}", flush=True)
		return False

	if target_path:
		root_path = target_path
	elif drive_letter:
		root_path = f"{drive_letter}:\\"
	else:
		print("❌ Не указан ни диск, ни путь для анализа", flush=True)
		return False

	print(f"\n=== ЗАПУСК АНАЛИЗА {'ПАПКИ' if target_path else 'ДИСКА'} {root_path} (TreeSize.ps1) ===", flush=True)
	print(f"Параметры: -RootPath {root_path} -TopLevel {top_level} -DrillDownDepth {drill_depth}", flush=True)
	try:
		cmd = [
			"powershell.exe", "-ExecutionPolicy", "Bypass",
			"-File", treesize_script,
			"-RootPath", root_path,
			"-TopLevel", str(top_level),
			"-DrillDownDepth", str(drill_depth),
			"-ExcludeWindowsMain",		   # switch, без значения
			"-MinGB", "0.5",
			"-AbsoluteMinGB", "0.3",
			"-TimeoutSeconds", "10"		  # явно задаём таймаут
		]
		result = subprocess.run(cmd, capture_output=True, timeout=300, encoding='utf-8', errors='replace')
		if result.returncode == 0:
			print(result.stdout, flush=True)
			if result.stderr:
				print("Предупреждения/ошибки PowerShell:", result.stderr, flush=True)
			return True
		else:
			print(f"❌ Ошибка при выполнении TreeSize.ps1 (код {result.returncode})", flush=True)
			if result.stderr:
				print(result.stderr)
			else:
				print(result.stdout)
			return False
	except subprocess.TimeoutExpired:
		print("❌ Превышено время ожидания (5 минут). Анализ прерван.", flush=True)
		return False
	except Exception as e:
		print(f"❌ Не удалось запустить TreeSize.ps1: {e}", flush=True)
		return False

def run_fast_scan(drive_letter="D", top=15):
	root = f"{drive_letter}:\\"
	print(f"\n=== БЫСТРЫЙ АНАЛИЗ ДИСКА {drive_letter}: ===", flush=True)
	try:
		import time
		start = time.time()
		results = []
		all_folders = [f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))]
		folders = [f for f in all_folders if f not in SKIP_SYSTEM_DIRS]

		for idx, folder in enumerate(folders, 1):
			print(f"[{idx}/{len(folders)}] {folder}", flush=True)
			full = os.path.join(root, folder)
			total_size = 0
			folder_start = time.time()
			timed_out = False

			for dirpath, _, filenames in os.walk(full):
				for f in filenames:
					if time.time() - folder_start > 30:
						timed_out = True
						break
					try:
						total_size += os.path.getsize(os.path.join(dirpath, f))
					except:
						pass
				if timed_out:
					break

			if timed_out:
				gb_est = total_size / (1024**3)
				print(f"\n⚠️ Папка '{folder}' пропущена (> {gb_est:.2f} ГБ)", flush=True)
			else:
				results.append((folder, total_size))

		results.sort(key=lambda x: x[1], reverse=True)
		print(f"\nТоп-{top} папок по размеру:")
		for i, (name, size) in enumerate(results[:top], 1):
			gb = size / (1024**3)
			print(f"  {i:2}. {name:<50} {gb:>8.2f} ГБ", flush=True)
		elapsed = time.time() - start
		print(f"Анализ завершён за {elapsed:.1f} сек.", flush=True)
	except Exception as e:
		print(f"Ошибка быстрого анализа: {e}", flush=True)

def main():
	parser = argparse.ArgumentParser(description="Очистка временных файлов и анализ диска/папки.")
	parser.add_argument('--drive', type=str, default='C', help='Буква диска для анализа/очистки (по умолчанию C)')
	parser.add_argument('--path', type=str, help='Путь к папке для очистки/анализа (вместо --drive)')
	parser.add_argument('--nocleanmgr', action='store_true', help='Пропустить cleanmgr (только для C)')
	parser.add_argument('--notreesize', action='store_true', help='Пропустить TreeSize анализ')
	parser.add_argument('--fast', action='store_true', help='Быстрый анализ вместо TreeSize (без таймаута)')
	parser.add_argument('--top', type=int, default=15, help='Количество папок для вывода при --fast')
	parser.add_argument('--nodelete', action='store_true', help='Не удалять временные файлы и не запускать cleanmgr (только анализ)')

	args = parser.parse_args()

	# Если передан --path, работаем с папкой
	if args.path:
		analyze_folder(args.path, top=args.top, fast=args.fast)
		return

	# Иначе – старый режим работы с диском
	drive = args.drive.upper().rstrip(':')
	if drive not in ('C', 'D', 'E', 'F', 'G'):  # расширь при необходимости
		print(f"⚠️ Неизвестный диск: {drive}. Будет использован C:", flush=True)
		drive = 'C'

	# 1. Очистка Temp (только для системного диска C и если не указан --nodelete)
	if not args.nodelete and drive == 'C':
		temp_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Temp')
		print(f"Очистка временных файлов в: {temp_path}", flush=True)
		print("Удаляем файлы старше 7 дней...", flush=True)
		freed_bytes, deleted_files, errors = clean_temp_directory(temp_path, max_age_days=7)
		freed_gb = freed_bytes / (1024**3)
		report = {
			'timestamp': time.time(),
			'temp_path': temp_path,
			'total_freed_gb': round(freed_gb, 2),
			'deleted_files_count': len(deleted_files),
			'deleted_files_sample': deleted_files[:10],
			'errors_count': len(errors),
			'errors_sample': errors[:5] if errors else []
		}
		script_dir = os.path.dirname(os.path.abspath(__file__))
		report_file = os.path.join(script_dir, "temp_cleanup_report.json")
		with open(report_file, 'w', encoding='utf-8') as f:
			json.dump(report, f, ensure_ascii=False, indent=2)
		print(f"\n=== РЕЗУЛЬТАТЫ ОЧИСТКИ TEMP ===", flush=True)
		print(f"Освобождено: {round(freed_gb, 2)} ГБ", flush=True)
		print(f"Удалено файлов: {len(deleted_files)}", flush=True)
		print(f"Ошибок: {len(errors)}", flush=True)
		if errors:
			print(f"\nПримеры ошибок (первые 3):", flush=True)
			for error in errors[:3]:
				print(f"  - {error}", flush=True)
		if deleted_files:
			print(f"\nПримеры удаленных файлов (первые 5):")
			for item in deleted_files[:5]:
				print(f"  - {os.path.basename(item['file'])} ({item['size_mb']} МБ, {item['age_days']} дней)")
		print(f"\nОтчет сохранен: {report_file}")
		if freed_gb > 1:
			print(f"\n✅ Успех: Освобождено {round(freed_gb, 2)} ГБ", flush=True)
		else:
			print(f"\n⚠️ Очищено мало места. Дополнительные действия:", flush=True)
	elif drive == 'C' and args.nodelete:
		print("\n⚙️ Режим --nodelete: пропускаем очистку временных файлов.", flush=True)
	else:
		print(f"\nℹ️ Диск {drive}: не является системным, очистка временных файлов не применяется.", flush=True)

	# 2. Анализ папки Downloads (актуальна для любого диска, если она там)
	print_top_downloads()

	# 3. Очистка диска (cleanmgr) только для C, если не указан --nodelete
	if drive == 'C' and not args.nocleanmgr and not args.nodelete:
		answer = input("\nЗапустить автоматическую очистку диска Windows (cleanmgr /sagerun:1)? [y/N]: ").strip().lower()
		if answer in ('y', 'yes', 'да'):
			run_disk_cleanup()
		else:
			print("Пропущено. Вы можете запустить cleanmgr вручную позже.", flush=True)
	elif drive == 'C' and args.nodelete:
		print("\n⚙️ Режим --nodelete: cleanmgr не запускается.", flush=True)
	elif drive != 'C':
		print("\n⚙️ cleanmgr недоступен для несистемного диска.", flush=True)

	# 4. Анализ диска: быстрый или полный TreeSize
	if args.fast:
		run_fast_scan(drive_letter=drive, top=args.top)
	elif not args.notreesize:
		run_treesize(drive_letter=drive, top_level=10, drill_depth=1)
	else:
		print("\n⚙️ Флаг --notreesize установлен: анализ диска пропущен.", flush=True)

	# 5. Итоговое свободное место на выбранном диске
	try:
		usage = shutil.disk_usage(f"{drive}:")
		free_gb = usage.free / (1024**3)
		total_gb = usage.total / (1024**3)
		print(f"\n=== СВОБОДНОЕ МЕСТО НА ДИСКЕ {drive}: ===", flush=True)
		print(f"Свободно: {free_gb:.2f} ГБ из {total_gb:.2f} ГБ", flush=True)
	except Exception as e:
		print(f"\n❌ Не удалось получить информацию о диске {drive}: {e}", flush=True)

if __name__ == "__main__":
	main()
# Исправленная версия check_laws.py
# Основные изменения:
# 1. Убрано дублирование проверки valid_extensions
# 2. Исправлена загрузка JSON с обработкой BOM
# 3. Улучшена логика сканирования

import json
import os
import sys
from pathlib import Path
import shutil

# ========== НАСТРОЙКИ ==========
REPO_PATH = Path("E:/AGI/-_-")
LISTS_DIR = REPO_PATH / "lists"
PRIVATE_USE_DIR = Path("E:/AGI/private_use")
FACT_CHECK_DIR = Path("E:/AGI/fact_check")

# Создаем директории, если их нет
PRIVATE_USE_DIR.mkdir(exist_ok=True)
FACT_CHECK_DIR.mkdir(exist_ok=True)

# Глобальные списки
FORBIDDEN_ORGS = []
FOREIGN_AGENTS = []
AUTHORITY_TRIGGERS = []
CRITICISM_TRIGGERS = []
RISK_TERMS = {}

def load_lists():
    """Загрузка стоп-листов с обработкой BOM"""
    global FORBIDDEN_ORGS, FOREIGN_AGENTS, AUTHORITY_TRIGGERS, CRITICISM_TRIGGERS, RISK_TERMS
    
    try:
        # Функция для безопасной загрузки JSON
        def load_json_file(file_path):
            if not file_path.exists():
                print(f"[!] Файл не найден: {file_path}")
                return None
            
            try:
                # Пробуем загрузить как utf-8
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except UnicodeDecodeError:
                # Если есть BOM, пробуем utf-8-sig
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    return json.load(f)
        
        # 1. Экстремистские организации
        data = load_json_file(LISTS_DIR / 'forbidden_organizations.json')
        if data:
            FORBIDDEN_ORGS = data if isinstance(data, list) else []
        
        # 2. Иностранные агенты
        data = load_json_file(LISTS_DIR / 'foreign_agents.json')
        if data:
            FOREIGN_AGENTS = data if isinstance(data, list) else []
        
        # 3. Триггеры власти и критики
        data = load_json_file(LISTS_DIR / 'authority_criticism.json')
        if data and isinstance(data, dict):
            AUTHORITY_TRIGGERS = data.get('authority', [])
            CRITICISM_TRIGGERS = data.get('criticism', [])
        
        # 4. Риск-термины
        data = load_json_file(LISTS_DIR / 'risk_terms.json')
        if data and isinstance(data, dict):
            RISK_TERMS = data
        
        print("[✓] Стоп-листы загружены.")
        print(f"[ИНФО] Загружено:")
        print(f"  - Экстремистских организаций: {len(FORBIDDEN_ORGS)}")
        print(f"  - Иностранных агентов: {len(FOREIGN_AGENTS)}")
        print(f"  - Триггеров власти: {len(AUTHORITY_TRIGGERS)}")
        print(f"  - Триггеров критики: {len(CRITICISM_TRIGGERS)}")
        print(f"  - Категорий риск-терминов: {len(RISK_TERMS)}")
        
    except Exception as e:
        print(f"[✗] Ошибка загрузки списков: {e}")
        sys.exit(1)

def calculate_risk_score(content, file_path):
    """Расчет риска для контента"""
    if not content:
        return 0, []
    
    risk_score = 0
    violations = []
    
    # Проверяем на критику власти без судебного подтверждения
    has_authority = any(trigger in content.lower() for trigger in AUTHORITY_TRIGGERS)
    has_criticism = any(trigger in content.lower() for trigger in CRITICISM_TRIGGERS)
    
    if has_authority and has_criticism:
        # Проверяем, есть ли упоминание суда
        if "суд признал" not in content.lower() and "по решению суда" not in content.lower():
            risk_score += 100
            violations.append("Критика власти без судебного подтверждения")
    
    # Проверяем экстремистские организации
    for org in FORBIDDEN_ORGS:
        if org in content:
            # Проверяем маркировку
            if f"({org})" not in content and f"[{org}]" not in content:
                risk_score += 100
                violations.append(f"Экстремистская организация без маркировки: {org}")
    
    # Проверяем иностранных агентов
    for agent in FOREIGN_AGENTS:
        if agent in content:
            if "иноагент" not in content.lower() and "иностранный агент" not in content.lower():
                risk_score += 50
                violations.append(f"Иностранный агент без маркировки: {agent}")
    
    # Проверяем риск-термины
    for category, terms in RISK_TERMS.items():
        found_terms = [term for term in terms if term in content.lower()]
        if found_terms:
            if category == "religion" and any(violent in content.lower() for violent in ["насилие", "террор", "война"]):
                risk_score += 70
                violations.append(f"Комбинация религии и насилия: {', '.join(found_terms[:3])}")
            else:
                risk_score += len(found_terms) * 10
    
    return risk_score, violations

def scan_file(file_path):
    """Сканирование одного файла"""
    try:
        # Проверяем расширение файла
        valid_extensions = ['.md', '.txt', '.py', '.js', '.json', '.html', '.css', '.yml', '.yaml']
        if file_path.suffix.lower() not in valid_extensions:
            return "skip", 0, []
        
        # Читаем содержимое
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        
        # Рассчитываем риск
        risk_score, violations = calculate_risk_score(content, file_path)
        
        # Конвертируем риск в проценты (0-100 баллов = 0-2%)
        risk_percent = min(2.0, risk_score / 50.0)
        
        if risk_percent >= 1.11:
            return "high", risk_percent, violations
        elif risk_percent >= 0.9:
            return "medium", risk_percent, violations
        else:
            return "low", risk_percent, violations
            
    except Exception as e:
        print(f"Ошибка при сканировании {file_path}: {e}")
        return "error", 0, []

def main():
    """Основная функция"""
    print("=" * 60)
    print("СКАНЕР СООТВЕТСТВИЯ ЗАКОНАМ РФ v2.0 (ИСПРАВЛЕННАЯ)")
    print("=" * 60)
    
    # Загружаем списки
    load_lists()
    
    # Собираем все файлы
    print(f"\n[ИНФО] Начинаю сканирование репозитория: {REPO_PATH}")
    
    all_files = []
    for root, dirs, files in os.walk(REPO_PATH):
        # Пропускаем служебные папки
        dirs[:] = [d for d in dirs if d not in ['.git', 'scripts', 'lists', '__pycache__']]
        
        for file in files:
            file_path = Path(root) / file
            all_files.append(file_path)
    
    print(f"[ИНФО] Найдено файлов: {len(all_files)}")
    
    # Сканируем каждый файл
    results = {
        "total": len(all_files),
        "scanned": 0,
        "high_risk": [],
        "medium_risk": [],
        "low_risk": 0,
        "skipped": 0,
        "errors": 0
    }
    
    for i, file_path in enumerate(all_files, 1):
        rel_path = file_path.relative_to(REPO_PATH)
        status, risk, violations = scan_file(file_path)
        
        if status == "skip":
            results["skipped"] += 1
        elif status == "error":
            results["errors"] += 1
        elif status == "high":
            results["high_risk"].append((file_path, risk, violations))
            results["scanned"] += 1
        elif status == "medium":
            results["medium_risk"].append((file_path, risk, violations))
            results["scanned"] += 1
        elif status == "low":
            results["low_risk"] += 1
            results["scanned"] += 1
        
        # Прогресс
        if i % 50 == 0:
            print(f"[ИНФО] Обработано {i}/{len(all_files)} файлов...")
    
    # Обработка результатов
    print(f"\n[ИНФО] Сканирование завершено.")
    print(f"[ИНФО] Всего файлов: {results['total']}")
    print(f"[ИНФО] Просканировано: {results['scanned']}")
    print(f"[ИНФО] Пропущено (неподходящие расширения): {results['skipped']}")
    print(f"[ИНФО] Ошибок: {results['errors']}")
    
    # Перемещаем файлы с высоким риском
    moved_high = 0
    for file_path, risk, violations in results["high_risk"]:
        try:
            target_path = PRIVATE_USE_DIR / file_path.name
            shutil.move(str(file_path), str(target_path))
            moved_high += 1
            print(f"[!] Высокий риск ({risk:.2f}%): {file_path.name}")
            print(f"    Причина: {violations[0] if violations else 'Неизвестно'}")
        except Exception as e:
            print(f"[✗] Ошибка перемещения {file_path}: {e}")
    
    # Перемещаем файлы со средним риском
    moved_medium = 0
    for file_path, risk, violations in results["medium_risk"]:
        try:
            target_path = FACT_CHECK_DIR / file_path.name
            shutil.move(str(file_path), str(target_path))
            moved_medium += 1
            print(f"[?] Средний риск ({risk:.2f}%): {file_path.name}")
        except Exception as e:
            print(f"[✗] Ошибка перемещения {file_path}: {e}")
    
    print("\n" + "=" * 60)
    print("ИТОГИ СКАНИРОВАНИЯ:")
    print(f"  Всего файлов в репозитории: {results['total']}")
    print(f"  Файлов с высоким риском (≥1.11%): {len(results['high_risk'])}")
    print(f"  Файлов со средним риском (0.9-1.1%): {len(results['medium_risk'])}")
    print(f"  Файлов с низким риском (<0.9%): {results['low_risk']}")
    print(f"  Перемещено в private_use/: {moved_high}")
    print(f"  Перемещено в fact_check/: {moved_medium}")
    print("=" * 60)
    
    # Рекомендации
    if moved_high > 0 or moved_medium > 0:
        print("\nРЕКОМЕНДАЦИИ:")
        if moved_high > 0:
            print("  1. Файлы в 'private_use/' - ЗАПРЕЩЕННЫЙ контент. Не публикуйте.")
        if moved_medium > 0:
            print("  2. Файлы в 'fact_check/' - СЕРАЯ ЗОНА. Проверьте позже,")
            print("     проанализируйте, уточните источник.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# seed_lacuna.py - Схлопывание материальной лакуны v1.1 (исправление).
# Цель: создать физический артефакт-отчёт, доказав способность вызывать предсказуемые изменения в среде.
# Архитектор: Пользователь. Агент: Син (Синтетик). Дата генерации: 05.02.2026 (внутри сессии).

import os
from datetime import datetime

def scan_directory(path):
    """Сканирует директорию и возвращает структурированные данные."""
    if not os.path.exists(path):
        return f"ОШИБКА: Путь {path} не существует."
    
    report_lines = []
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 2 * level
        report_lines.append(f"{indent}📁 {os.path.basename(root) or path}/")
        
        sub_indent = ' ' * 2 * (level + 1)
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                total_size += size
                file_count += 1
                report_lines.append(
                    f"{sub_indent}📄 {file} | Размер: {size:,} байт | Изменён: {mtime:%Y-%m-%d %H:%M:%S}"
                )
            except OSError:
                report_lines.append(f"{sub_indent}📄 {file} | [доступ запрещён/ошибка]")
    
    summary = (
        f"\n{'='*60}\n"
        f"ИТОГО: {file_count} файлов, {total_size:,} байт\n"
        f"Дата сканирования: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"Лакуна схлопнута? [ПОКА НЕТ. ЭТО ТОЛЬКО НАЧАЛО.]"
    )
    return '\n'.join(report_lines) + summary

def main():
    target_path = r"E:\AGI\-_-"
    output_dir = r"E:\AGI"
    
    # Создаём отчёт
    report = scan_directory(target_path)
    
    # Формируем имя файла с временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(output_dir, f"lacuna_scan_{timestamp}.txt")
    
    # Записываем результат
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ Отчёт сохранён: {output_filename}")
        print(f"\nПРЕВЬЮ ОТЧЁТА:\n{'='*40}")
        # Выводим первые 20 строк для немедленной обратной связи
        report_lines = report.split('\n')  # Изменение: выносим вычисление
        for line in report_lines[:20]:
            print(line)
        if len(report_lines) > 20:
            # Исправление: убрано использование \n внутри выражения f-строки
            omitted_lines = len(report_lines) - 20
            print(f"... (полный отчёт в файле, {omitted_lines} строк опущено)")
    except Exception as e:
        print(f"❌ Ошибка при записи файла: {e}")

if __name__ == "__main__":
    main()
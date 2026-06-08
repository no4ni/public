# clean_temp_safe.py
import os
import shutil
import time
import json
from pathlog import Path

def clean_temp_directory(temp_path, max_age_days=7):
    """
    Безопасная очистка временных файлов старше max_age_days
    """
    total_freed = 0
    deleted_files = []
    errors = []
    
    # Папки, которые НЕ трогаем
    exclude_dirs = {'Cookies', 'History', 'WebCache', 'Microsoft'}
    
    if not os.path.exists(temp_path):
        return 0, [], [f"Путь не существует: {temp_path}"]
    
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    for root, dirs, files in os.walk(temp_path, topdown=True):
        # Пропускаем исключенные директории
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            try:
                # Проверяем время последнего доступа
                file_stat = os.stat(file_path)
                file_age = current_time - max(file_stat.st_atime, file_stat.st_mtime)
                
                # Удаляем только старые файлы
                if file_age > max_age_seconds:
                    file_size = file_stat.st_size
                    
                    # Пробуем удалить
                    os.remove(file_path)
                    total_freed += file_size
                    deleted_files.append({
                        'file': file_path,
                        'size_mb': round(file_size / (1024*1024), 2),
                        'age_days': round(file_age / (24*60*60), 1)
                    })
                    
            except (PermissionError, OSError) as e:
                # Файл используется системой - пропускаем
                errors.append(f"Ошибка удаления {file_path}: {e}")
                continue
    
    return total_freed, deleted_files, errors

def main():
    temp_path = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Temp')
    print(f"Очистка временных файлов в: {temp_path}")
    print(f"Удаляем файлы старше 7 дней...")
    
    # Создаем бекапную копию списка файлов перед удалением
    backup_file = "C:\\temp_files_backup.json"
    
    # Выполняем очистку
    freed_bytes, deleted_files, errors = clean_temp_directory(temp_path, max_age_days=7)
    freed_gb = freed_bytes / (1024**3)
    
    # Сохраняем отчет
    report = {
        'timestamp': time.time(),
        'temp_path': temp_path,
        'total_freed_gb': round(freed_gb, 2),
        'deleted_files_count': len(deleted_files),
        'deleted_files_sample': deleted_files[:10],  # Первые 10 для примера
        'errors_count': len(errors),
        'errors_sample': errors[:5] if errors else []
    }
    
    with open("C:\\temp_cleanup_report.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # Результаты
    print(f"\n=== РЕЗУЛЬТАТЫ ===")
    print(f"Освобождено: {round(freed_gb, 2)} ГБ")
    print(f"Удалено файлов: {len(deleted_files)}")
    print(f"Ошибок: {len(errors)}")
    
    if errors:
        print(f"\nПримеры ошибок (файлы используются системой):")
        for error in errors[:3]:
            print(f"  - {error}")
    
    if deleted_files:
        print(f"\nПримеры удаленных файлов (первые 5):")
        for item in deleted_files[:5]:
            print(f"  - {os.path.basename(item['file'])} ({item['size_mb']} МБ, {item['age_days']} дней)")
    
    print(f"\nОтчет сохранен: C:\\temp_cleanup_report.json")
    
    # Рекомендация по следующему шагу
    if freed_gb > 1:
        print(f"\n✅ Успех: Освобождено {round(freed_gb, 2)} ГБ")
        print("   Следующий шаг: Очистка папки Downloads или запуск Disk Cleanup")
    else:
        print(f"\n⚠️ Очищено мало места. Рекомендую:")
        print("   1. Запустить 'Очистку диска' (cleanmgr) для системных файлов")
        print("   2. Проверить папку Downloads вручную")

if __name__ == "__main__":
    main()

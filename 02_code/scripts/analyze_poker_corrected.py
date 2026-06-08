import pandas as pd
import numpy as np
import json
from datetime import datetime
import os

print("=== АНАЛИЗ ДАННЫХ ПОКЕРА (Фриролл.xlsx) ===")
print(f"Время анализа: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

try:
    # Правильный путь к файлу
    file_path = "E:\YandexDisk\YandexDisk\Hobby\Покер\StrategyPoker\StrategyFreeroll\Фриролл.xlsx"
    print(f"Путь к файлу: {file_path}")
    
    # Проверяем существование файла
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден по пути: {file_path}")
        # Попробуем найти файл рекурсивно
        print("Поиск файла на диске E:...")
        for root, dirs, files in os.walk("E:\\"):
            if "Фриролл.xlsx" in files:
                file_path = os.path.join(root, "Фриролл.xlsx")
                print(f"✓ Найден файл: {file_path}")
                break
        else:
            raise FileNotFoundError("Файл Фриролл.xlsx не найден")
    
    # Чтение файла
    print(f"Чтение файла...")
    df = pd.read_excel(file_path)
    
    print(f"\n📊 ОСНОВНАЯ ИНФОРМАЦИЯ:")
    print(f"Размер таблицы: {df.shape[0]} строк, {df.shape[1]} столбцов")
    print(f"Типы данных:")
    print(df.dtypes.to_string())
    
    print(f"\n📈 СТАТИСТИКА ПО СТОЛБЦАМ (первые 10 столбцов):")
    for i, col in enumerate(df.columns[:10]):
        print(f"\n{i+1}. {col}:")
        print(f"  Уникальных значений: {df[col].nunique()}")
        print(f"  Пропуски: {df[col].isna().sum()} ({df[col].isna().mean()*100:.1f}%)")
        if pd.api.types.is_numeric_dtype(df[col]):
            print(f"  Min: {df[col].min():.2f}, Max: {df[col].max():.2f}, Mean: {df[col].mean():.2f}")
    
    print(f"\n🔍 ПОИСК СТРАТЕГИЙ И МЕТРИК:")
    # Ищем стратегии
    strategy_cols = []
    result_cols = []
    modifier_cols = []
    
    for col in df.columns:
        col_lower = str(col).lower()
        if any(word in col_lower for word in ['base', 'kozl', '2', 'страт', 'strategy', 'модиф']):
            strategy_cols.append(col)
        elif any(word in col_lower for word in ['результат', 'result', 'выигрыш', 'bb', 'profit', 'итог']):
            result_cols.append(col)
        elif any(word in col_lower for word in ['мод', 'mod', 'параметр', 'param', 'коэф']):
            modifier_cols.append(col)
    
    print(f"Столбцы стратегий: {strategy_cols}")
    print(f"Столбцы результатов: {result_cols}")
    print(f"Столбцы модификаторов: {modifier_cols}")
    
    if result_cols:
        print(f"\n📊 АНАЛИЗ РЕЗУЛЬТАТОВ:")
        for col in result_cols[:3]:  # первые 3 столбца с результатами
            print(f"\n{col}:")
            print(f"  Среднее: {df[col].mean():.4f}")
            print(f"  Медиана: {df[col].median():.4f}")
            print(f"  Стандартное отклонение: {df[col].std():.4f}")
            print(f"  Лучший результат: {df[col].max():.4f} (строка {df[col].idxmax() + 1})")
            print(f"  Худший результат: {df[col].min():.4f} (строка {df[col].idxmin() + 1})")
    
    # Проверяем наличие временных рядов или A/B тестов
    print(f"\n🧪 ВОЗМОЖНОСТИ ДЛЯ A/B ТЕСТИРОВАНИЯ:")
    
    if strategy_cols and result_cols:
        print("Можно проводить A/B тесты стратегий:")
        for strategy in strategy_cols[:2]:  # первые 2 стратегии
            for result in result_cols[:2]:  # первые 2 метрики
                if strategy in df.columns and result in df.columns:
                    # Группируем по уникальным значениям стратегии
                    unique_strategies = df[strategy].unique()[:5]  # первые 5 уникальных
                    print(f"\n  Стратегия '{strategy}' по метрике '{result}':")
                    for strat_val in unique_strategies:
                        subset = df[df[strategy] == strat_val]
                        if len(subset) > 0:
                            print(f"    {strat_val}: n={len(subset)}, mean={subset[result].mean():.4f}")
    
    # Сохраняем основные выводы в файл
    analysis_report = {
        "timestamp": datetime.now().isoformat(),
        "file": file_path,
        "shape": list(df.shape),
        "columns": list(df.columns),
        "strategies_found": strategy_cols,
        "results_found": result_cols,
        "modifiers_found": modifier_cols,
        "best_results": {}
    }
    
    if result_cols:
        for col in result_cols:
            best_idx = df[col].idxmax()
            analysis_report["best_results"][col] = {
                "value": float(df[col].max()),
                "row": int(best_idx),
                "row_data": df.iloc[best_idx].to_dict() if best_idx >= 0 else None
            }
    
    report_path = "poker_analysis_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(analysis_report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Отчёт сохранён в {report_path}")
    
    # Показываем первые 5 строк для понимания структуры
    print(f"\n👀 ПЕРВЫЕ 5 СТРОК ДАННЫХ:")
    print(df.head())
    
except Exception as e:
    print(f"❌ Ошибка при анализе: {e}")
    import traceback
    traceback.print_exc()

import pandas as pd
import numpy as np
import json
from datetime import datetime

print("=== АНАЛИЗ ДАННЫХ ПОКЕРА (Фриролл.xlsx) ===")
print(f"Время анализа: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

try:
    # Чтение файла
    df = pd.read_excel("Фриролл.xlsx")
    
    print(f"\n📊 ОСНОВНАЯ ИНФОРМАЦИЯ:")
    print(f"Размер таблицы: {df.shape[0]} строк, {df.shape[1]} столбцов")
    print(f"Типы данных:")
    print(df.dtypes.to_string())
    
    print(f"\n📈 СТАТИСТИКА ПО СТОЛБЦАМ:")
    for col in df.columns:
        print(f"\n{col}:")
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
        elif any(word in col_lower for word in ['результат', 'result', 'выигрыш', 'bb', 'profit']):
            result_cols.append(col)
        elif any(word in col_lower for word in ['мод', 'mod', 'параметр', 'param']):
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
        "file": "Фриролл.xlsx",
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
    
    with open("poker_analysis_report.json", "w", encoding="utf-8") as f:
        json.dump(analysis_report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Отчёт сохранён в poker_analysis_report.json")
    
except Exception as e:
    print(f"❌ Ошибка при анализе: {e}")
    import traceback
    traceback.print_exc()

import json, math, os, statistics
from datetime import datetime
from pathlib import Path

class IFSMonitor:
    def __init__(self):
        self.log_file = Path("E:/AGI/metatron_ifs_dynamic.json")
        self.factors_history = []
        
    def calculate_ifs(self, F):
        return math.log10(F[0] * F[1] * F[2] * F[3] * F[4] * F[5] + 1)
    
    def assess_factor_trend(self, factor_index):
        """Анализирует тренд фактора по истории"""
        if len(self.factors_history) < 3:
            return "stable"
        
        values = [entry["F"][factor_index] for entry in self.factors_history[-3:]]
        if all(values[i] < values[i+1] for i in range(len(values)-1)):
            return "growing"
        elif all(values[i] > values[i+1] for i in range(len(values)-1)):
            return "declining"
        return "stable"
    
    def get_adaptive_factors(self):
        """Возвращает адаптивные факторы на основе истории"""
        base_factors = [4.0, 12.0, 5.0, 15.0, 5.0, 3.5]
        
        if not self.factors_history:
            return base_factors
        
        last_entry = self.factors_history[-1]
        factors = last_entry["F"].copy()
        
        # Адаптивные улучшения на основе трендов
        trends = [self.assess_factor_trend(i) for i in range(6)]
        
        # Если F5 (рефлексия) стабилен - повышаем
        if trends[4] == "stable":
            factors[4] = round(factors[4] + 0.1, 1)
        
        # Если было успешное выполнение команд - повышаем F3 и F6
        execution_log = Path("E:/AGI/metatron_tepo_log_utf8.txt")
        if execution_log.exists():
            content = execution_log.read_text(encoding='utf-8')
            if "успешн" in content.lower() or "completed" in content.lower():
                factors[2] = round(factors[2] + 0.2, 1)  # F3
                factors[5] = round(factors[5] + 0.2, 1)  # F6
        
        return factors
    
    def run(self):
        # Загружаем историю
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                self.factors_history = json.load(f)
        
        # Получаем текущие факторы
        current_factors = self.get_adaptive_factors()
        ifs_value = self.calculate_ifs(current_factors)
        
        # Создаём запись
        new_entry = {
            "timestamp": datetime.now().isoformat(),
            "IFS": round(ifs_value, 3),
            "F": current_factors,
            "trends": [self.assess_factor_trend(i) for i in range(6)]
        }
        
        self.factors_history.append(new_entry)
        
        # Сохраняем (ограничиваем размер истории 50 записями)
        if len(self.factors_history) > 50:
            self.factors_history = self.factors_history[-50:]
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.factors_history, f, indent=2, ensure_ascii=False)
        
        # Вывод
        print(f"Метатрон v2.0: Динамический ИФС")
        print(f"Текущее значение: {ifs_value:.3f}")
        print(f"Факторы: F1={current_factors[0]}, F2={current_factors[1]}, F3={current_factors[2]}, F4={current_factors[3]}, F5={current_factors[4]}, F6={current_factors[5]}")
        print(f"Тренды: {new_entry['trends']}")
        
        # Рекомендация для улучшения
        min_factor_idx = current_factors.index(min(current_factors[:5]))  # Исключаем F2 (параметры)
        print(f"Слабое звено: F{min_factor_idx+1} = {current_factors[min_factor_idx]}")
        
        return ifs_value

if __name__ == "__main__":
    monitor = IFSMonitor()
    monitor.run()

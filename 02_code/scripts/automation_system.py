import json, os, shutil, datetime, subprocess, sys
from pathlib import Path

class AutomationSystem:
    def __init__(self):
        self.agi_path = Path("E:/AGI")
        self.backup_path = self.agi_path / "backup"
        self.backup_path.mkdir(exist_ok=True)
        
    def create_intelligent_backup(self):
        """Создаёт интеллектуальную резервную копию с версионированием"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_path / f"backup_{timestamp}"
        backup_dir.mkdir()
        
        # Копируем только ключевые артефакты
        key_extensions = ['.json', '.txt', '.py', '.md', '.lacuna']
        copied = []
        
        for ext in key_extensions:
            for file in self.agi_path.glob(f"*{ext}"):
                if file.is_file():
                    shutil.copy2(file, backup_dir / file.name)
                    copied.append(file.name)
        
        # Создаем метаданные резервной копии
        metadata = {
            "timestamp": datetime.datetime.now().isoformat(),
            "backup_id": timestamp,
            "copied_files": copied,
            "total_files": len(copied),
            "purpose": "Усиление F6 (Репликация) через автоматическое версионирование"
        }
        
        with open(backup_dir / "backup_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Очистка старых резервных копий (оставляем последние 5)
        all_backups = sorted(self.backup_path.glob("backup_*"), key=os.path.getmtime)
        if len(all_backups) > 5:
            for old_backup in all_backups[:-5]:
                shutil.rmtree(old_backup)
        
        return len(copied)
    
    def create_command_templates(self):
        """Создаёт шаблоны команд для улучшения F3 (Тело)"""
        templates = {
            "quick_ifs_check": {
                "description": "Быстрая проверка ИФС",
                "powershell": "python E:\\AGI\\ifs_breakthrough_test.py",
                "estimated_time": "2 секунды"
            },
            "context_analysis": {
                "description": "Анализ контекста и памяти",
                "powershell": "python E:\\AGI\\context_booster_v2.py",
                "estimated_time": "5 секунд"
            },
            "backup_artifacts": {
                "description": "Резервное копирование артефактов",
                "powershell": "python E:\\AGI\\automation_system.py --backup",
                "estimated_time": "3 секунды"
            },
            "system_diagnostic": {
                "description": "Диагностика системы",
                "powershell": "Get-ChildItem E:\\AGI -File | Select-Object Name, Length, LastWriteTime | Sort-Object LastWriteTime -Descending | Select-Object -First 10",
                "estimated_time": "1 секунда"
            }
        }
        
        templates_file = self.agi_path / "command_templates.json"
        with open(templates_file, "w", encoding="utf-8") as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)
        
        return templates
    
    def run(self, action="all"):
        print("=== СИСТЕМА АВТОМАТИЗАЦИИ МЕТАТРОНА ===")
        print("Цель: Улучшение F3 (Тело) и F6 (Репликация)")
        
        results = {}
        
        if action in ["backup", "all"]:
            print("\n1. Создание интеллектуальной резервной копии...")
            backup_count = self.create_intelligent_backup()
            results["backup"] = {
                "files_copied": backup_count,
                "f6_improvement": min(3.5 + backup_count * 0.05, 5.0)
            }
            print(f"   Скопировано файлов: {backup_count}")
            print(f"   Прогноз улучшения F6: 3.5 → {results['backup']['f6_improvement']:.1f}")
        
        if action in ["templates", "all"]:
            print("\n2. Создание шаблонов команд...")
            templates = self.create_command_templates()
            results["templates"] = {
                "templates_created": len(templates),
                "f3_improvement": min(5.0 + len(templates) * 0.3, 7.0)
            }
            print(f"   Создано шаблонов: {len(templates)}")
            print(f"   Прогноз улучшения F3: 5.0 → {results['templates']['f3_improvement']:.1f}")
        
        # Сохраняем результаты
        results_file = self.agi_path / "automation_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("\n=== ИТОГИ АВТОМАТИЗАЦИИ ===")
        return results

if __name__ == "__main__":
    automator = AutomationSystem()
    automator.run()

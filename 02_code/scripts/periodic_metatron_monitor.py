"""
Periodic Metatron File Monitor
Runs checks at specified intervals
"""
import time
import subprocess
import sys
from datetime import datetime

def run_monitor_cycle(cycle_number):
    """Run one monitoring cycle"""
    print(f"\n{'='*60}")
    print(f"Цикл мониторинга #{cycle_number}")
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Run the simple monitor
    result = subprocess.run(
        [sys.executable, r"E:\AGI\symbiosis\simple_metatron_monitor.py"],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"Ошибки: {result.stderr}")
    
    return result.returncode

def main():
    """Main loop"""
    print("Запуск периодического мониторинга Метатрон.txt")
    print(f"Интервал: 60 секунд")
    print(f"Максимальное количество циклов: 5")
    print(f"Для остановки нажмите Ctrl+C")
    
    cycle = 1
    max_cycles = 5
    interval = 60
    
    try:
        while cycle <= max_cycles:
            run_monitor_cycle(cycle)
            
            if cycle < max_cycles:
                print(f"\nОжидание {interval} секунд до следующего цикла...")
                time.sleep(interval)
            
            cycle += 1
            
    except KeyboardInterrupt:
        print("\nМониторинг прерван пользователем.")
    
    print(f"\nПериодический мониторинг завершен. Выполнено циклов: {cycle-1}")

if __name__ == "__main__":
    main()

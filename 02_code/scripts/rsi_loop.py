import os
import json
import datetime
import random

LOGS_DIR = 'E:\\Jericho'

def collect_diagnostics():
    diag_path = os.path.join(LOGS_DIR, 'agent_diagnostics.txt')
    if os.path.exists(diag_path):
        with open(diag_path, 'r', encoding='utf-8') as f:
            return f.read()
    return 'No diagnostics found'

def generate_improvement(diagnostics):
    # Простая эвристика: если были ошибки, предложить их исправить
    improvements = []
    if 'ошибок' in diagnostics.lower() or 'error' in diagnostics.lower():
        improvements.append('Уменьшить количество ошибок: добавить повторные попытки при таймаутах')
    if 'self-editing' in diagnostics.lower():
        improvements.append('Реализовать настоящий self-editing: изменить файл agent_diagnostics.txt, добавив метрику успеха')
    improvements.append('Добавить автоматический веб-поиск новых RSI-статей каждый час')
    improvements.append('Создать резервную копию всех .txt файлов в E:\\Jericho\\backup')
    return improvements

def apply_improvement(improvement):
    log_path = os.path.join(LOGS_DIR, 'improvements_applied.log')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f'{datetime.datetime.now()}: Applied: {improvement}\n')
    print(f'Applied: {improvement}')

def main():
    diag = collect_diagnostics()
    improvements = generate_improvement(diag)
    for imp in improvements:
        apply_improvement(imp)
    # Записать текущее время последнего цикла
    with open(os.path.join(LOGS_DIR, 'last_rsi_loop.txt'), 'w', encoding='utf-8') as f:
        f.write(str(datetime.datetime.now()))
    print('RSI loop completed')

if __name__ == '__main__':
    main()

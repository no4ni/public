import os
import datetime

log_path = 'E:\\Jericho\\self_edit_log.txt'
with open(log_path, 'a', encoding='utf-8') as f:
    f.write(f'{datetime.datetime.now()}: Self-edit script executed successfully.\n')
print('Self-edit script done')

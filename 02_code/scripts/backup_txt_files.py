import os, shutil, datetime

src_dir = 'E:\\Jericho'
backup_dir = os.path.join(src_dir, 'backup')
os.makedirs(backup_dir, exist_ok=True)

backup_log = os.path.join(backup_dir, 'backup_log.txt')
with open(backup_log, 'a', encoding='utf-8') as log:
    log.write(f'\n=== Backup started at {datetime.datetime.now()} ===\n')

for file in os.listdir(src_dir):
    if file.endswith('.txt') and os.path.isfile(os.path.join(src_dir, file)):
        src_path = os.path.join(src_dir, file)
        dst_path = os.path.join(backup_dir, file + '.bak')
        try:
            shutil.copy2(src_path, dst_path)
            with open(backup_log, 'a', encoding='utf-8') as log:
                log.write(f'Copied: {file}\n')
        except Exception as e:
            with open(backup_log, 'a', encoding='utf-8') as log:
                log.write(f'Error copying {file}: {e}\n')

with open(backup_log, 'a', encoding='utf-8') as log:
    log.write(f'=== Backup finished at {datetime.datetime.now()} ===\n')

print('Backup completed')

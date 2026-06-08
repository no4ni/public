import os
import shutil

def get_size(path):
    total = 0
    for entry in os.scandir(path):
        try:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_size(entry.path)
        except (PermissionError, FileNotFoundError):
            pass
    return total

targets = [
    os.environ['USERPROFILE'] + r'\Downloads',
    os.environ['USERPROFILE'] + r'\Documents',
    os.environ['USERPROFILE'] + r'\Videos',
    os.environ['USERPROFILE'] + r'\Music',
    os.environ['TEMP'],
    r'C:\Windows\Temp'
]

print("Disk usage analysis (GB):")
for t in targets:
    if os.path.exists(t):
        size = get_size(t) / (1024**3)
        print(f"{t}: {size:.2f} GB")

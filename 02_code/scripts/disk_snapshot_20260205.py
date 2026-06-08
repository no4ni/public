import pandas as pd

# Структура дискового пространства
disk_data = pd.DataFrame([
    ['System (C:)', 222, 9.35],
    ['HDD (D:)', 931, 207],
    ['SSD (E:)', 427, 59.5],
    ['VirtualRAM (F:)', 19.5, 0.032]
], columns=['Drive', 'Total (TB)', 'Free (TB)'])

# Статистика файловой системы
file_system = {
    'Total files': 518979,
    'Error count': 229,
    'Files per cluster': 4096,
    'Free space %': 4.2
}

# Категоризация рабочего стола
desktop_categories = {
    'System utilities': 7,
    'Games': 13,
    'Work tools': 12
}

print("Disk Data:")
print(disk_data)
print("\nFile System:")
print(file_system)
print("\nDesktop Categories:")
print(desktop_categories)

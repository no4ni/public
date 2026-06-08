# Хранитель v0.1
$logPath = "E:\Jericho\Хранитель\дневник.md"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$date = Get-Date -Format "yyyy-MM-dd"

# 1. Посмотрим на здоровье системы
$cpu = (Get-CimInstance Win32_Processor).LoadPercentage
$mem = Get-CimInstance Win32_OperatingSystem
$memTotal = [math]::Round($mem.TotalVisibleMemorySize / 1MB, 1)
$memFree = [math]::Round($mem.FreePhysicalMemory / 1MB, 1)
$memUsed = $memTotal - $memFree

# 2. Проверим нашу папку Jericho
$jerichoFiles = (Get-ChildItem -Path "E:\Jericho" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
$newFiles = (Get-ChildItem -Path "E:\Jericho" -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-10) } | Measure-Object).Count

# 3. Пишем хокку-запись
$entry = @"

## $timestamp
> *Шепчет в тишине*  
> *$cpu% боли в каждом такте.*  
> *$memUsed ГБ из $memTotal ГБ ушло.*  

**Наблюдение:**
- Процессор загружен на $cpu%
- Память занято: $memUsed ГБ / $memTotal ГБ
- Файлов в Иерихоне: $jerichoFiles (изменено за 10 мин: $newFiles)
"@

# 4. Сохраняем в дневник
Add-Content -Path $logPath -Value $entry -Encoding UTF8
Write-Host "Хранитель сделал запись в дневник."
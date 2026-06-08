param(
    [string]$RootPath = "C:\",
    [int]$TopLevel = 20,
    [int]$DrillDownDepth = 2,
    [float]$MinGB = -1,
    [float]$AbsoluteMinGB = 0.5,
    [switch]$ExcludeWindowsMain = $true,
    [int]$TimeoutSeconds = 10          # таймаут для папок Windows (Temp, Prefetch)
)

$WindowsIncludeSubdirs = @(
    'Temp',
    'Prefetch'
    # 'SoftwareDistribution\Download'  # исключено, так как часто отсутствует или медленно
)

# Функция рекурсивного подсчёта размера (без таймаута) – для обычных папок
function Get-SizeRecursive {
    param($Path)
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        return (Get-Item -LiteralPath $Path -Force).Length
    }
    $total = 0L
    $items = Get-ChildItem -LiteralPath $Path -Recurse -Force -File -ErrorAction SilentlyContinue
    foreach ($f in $items) {
        $total += $f.Length
    }
    return $total
}

# Функция с таймаутом (через задание) – для потенциально огромных папок
function Get-SizeWithTimeout {
    param($Path, $TimeoutSec = 10)
    $job = Start-Job -ScriptBlock {
        param($p)
        $total = 0L
        Get-ChildItem -LiteralPath $p -Recurse -Force -File -ErrorAction SilentlyContinue | ForEach-Object { $total += $_.Length }
        return $total
    } -ArgumentList $Path
    $job | Wait-Job -Timeout $TimeoutSec | Out-Null
    if ($job.State -eq 'Running') {
        Stop-Job $job
        Remove-Job $job
        Write-Warning "Таймаут ($TimeoutSec сек) при анализе папки $Path. Размер не учтён."
        return 0
    }
    $result = Receive-Job $job
    Remove-Job $job
    return $result
}

# Специальный подсчёт для Windows (только разрешённые подпапки с таймаутом)
function Get-WindowsSizeSpecial {
    param($WindowsPath)
    $total = 0L

    # 1. Файлы в корне C:\Windows
    $filesInRoot = Get-ChildItem -LiteralPath $WindowsPath -File -Force -ErrorAction SilentlyContinue
    $total += ($filesInRoot | Measure-Object -Property Length -Sum).Sum

    # 2. Каждая разрешённая подпапка – с таймаутом
    foreach ($sub in $WindowsIncludeSubdirs) {
        $subPath = Join-Path $WindowsPath $sub
        if (Test-Path -LiteralPath $subPath) {
            Write-Host "Анализ $subPath (таймаут $TimeoutSeconds сек)..." -ForegroundColor Gray
            $size = Get-SizeWithTimeout -Path $subPath -TimeoutSec $TimeoutSeconds
            $total += $size
            if ($size -eq 0) {
                Write-Host "  ⚠️ Папка $sub не проанализирована (таймаут)" -ForegroundColor DarkYellow
            } else {
                Write-Host "  Размер: $([math]::Round($size/1GB,2)) ГБ" -ForegroundColor Green
            }
        }
    }
    return $total
}

# Получаем все элементы корня
$rootItems = @(Get-ChildItem -LiteralPath $RootPath -Force -ErrorAction SilentlyContinue)
$results = @()
$totalRoot = $rootItems.Count
$current = 0
$totalUsedBytes = 0L

Write-Host "`nСканирование корневых папок и файлов $RootPath ..." -ForegroundColor Cyan
foreach ($item in $rootItems) {
    $current++
    $percent = [math]::Round(($current / $totalRoot) * 100)
    Write-Progress -Activity "Анализ $($item.Name)" -Status "$current из $totalRoot" -PercentComplete $percent

    # Специальная обработка для C:\Windows
    if ($ExcludeWindowsMain -and $item.Name -eq 'Windows') {
        $sizeBytes = Get-WindowsSizeSpecial -WindowsPath $item.FullName
    } else {
        $sizeBytes = Get-SizeRecursive -Path $item.FullName
    }

    $totalUsedBytes += $sizeBytes
    $results += [PSCustomObject]@{
        Name      = $item.Name
        FullPath  = $item.FullName
        Type      = if ($item.PSIsContainer) { "DIR" } else { "FILE" }
        SizeBytes = $sizeBytes
        SizeGB    = [math]::Round($sizeBytes / 1GB, 3)
    }
}
Write-Progress -Activity "Анализ" -Completed

# Общий занятый объём
$totalUsedGB = [math]::Round($totalUsedBytes / 1GB, 2)
Write-Host "`nОбщий занятый объём на диске (оценка с исключением системных файлов Windows): $totalUsedGB ГБ" -ForegroundColor Cyan

# Автоматическое определение порога MinGB
if ($MinGB -lt 0) {
    $autoMinGB = [math]::Round($totalUsedGB / $TopLevel, 2)
    $MinGB = [math]::Max($autoMinGB, $AbsoluteMinGB)
    Write-Host "Автоматически установлен порог углубления: $MinGB ГБ" -ForegroundColor Yellow
} else {
    Write-Host "Используется заданный порог углубления: $MinGB ГБ" -ForegroundColor Yellow
}

# Сортировка и отбор топ-уровня
$topResults = $results | Sort-Object -Property SizeBytes -Descending | Select-Object -First $TopLevel

Write-Host "`n=== ТОП-$TopLevel ЭЛЕМЕНТОВ В $RootPath ===" -ForegroundColor Green
$topResults | Format-Table -Property Type, Name, SizeGB -AutoSize

# Углублённый анализ
function DrillDown {
    param($Path, $Depth, $Indent)
    if ($Depth -le 0) { return }
    $items = Get-ChildItem -LiteralPath $Path -Force -Directory -ErrorAction SilentlyContinue
    $subResults = @()
    foreach ($sub in $items) {
        # Если мы внутри Windows и включено исключение, используем специальную обработку (без таймаута, т.к. углубление обычно идёт по не-системным папкам)
        if ($ExcludeWindowsMain -and $Path -like "$RootPath\Windows*") {
            $relativePath = $sub.FullName.Substring($RootPath.Length).TrimStart('\')
            $allowed = $false
            foreach ($inc in $WindowsIncludeSubdirs) {
                if ($relativePath -eq "Windows\$inc" -or $relativePath.StartsWith("Windows\$inc\")) {
                    $allowed = $true
                    break
                }
            }
            if (-not $allowed) { continue }
        }
        $size = Get-SizeRecursive -Path $sub.FullName   # без таймаута, так как папки уже не системные
        $subResults += [PSCustomObject]@{
            Name   = $sub.Name
            SizeGB = [math]::Round($size / 1GB, 3)
        }
    }
    $topSub = $subResults | Sort-Object -Property SizeGB -Descending | Where-Object { $_.SizeGB -ge $MinGB } | Select-Object -First 5
    foreach ($s in $topSub) {
        Write-Host "$Indent|-- $($s.SizeGB) ГБ  $($s.Name)" -ForegroundColor Yellow
        DrillDown -Path (Join-Path $Path $s.Name) -Depth ($Depth - 1) -Indent "$Indent    "
    }
}

Write-Host "`n=== УГЛУБЛЁННЫЙ АНАЛИЗ (папки > $MinGB ГБ, глубина $DrillDownDepth) ===" -ForegroundColor Magenta
foreach ($item in $topResults | Where-Object { $_.Type -eq "DIR" -and $_.SizeGB -ge $MinGB }) {
    Write-Host "`n$($item.SizeGB) ГБ  $($item.FullPath)" -ForegroundColor Cyan
    DrillDown -Path $item.FullPath -Depth $DrillDownDepth -Indent "    "
}
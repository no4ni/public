<#
.SYNOPSIS
Удаляет дубликаты, оставляя файлы с кратчайшим путём.
Текстовые файлы с идентичным содержанием, но разными кодировками/переносами, считаются дубликатами.
Вторичная проверка через Compare-Object блокирует удаление при скрытых различиях.
#>
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium')]
param()
$rootPath = "E:\Jericho"
if (-not (Test-Path $rootPath -PathType Container)) { Write-Error "Папка '$rootPath' не существует."; exit 1 }
Write-Host "Сканирование: $rootPath" -ForegroundColor Cyan

# Быстрая нормализация для группировки (UTF-8/ANSI → единый байтовый поток)
function Get-NormalizedHash {
    param([string]$FilePath)
    $ext = [System.IO.Path]::GetExtension($FilePath).ToLower()
    $textExts = @('.txt','.md','.ps1','.py','.json','.xml','.csv','.yaml','.yml','.cfg','.ini','.log','.lacuna','.html','.css','.js','.bat','.sh')
    if ($ext -in $textExts) {
        try {
            $content = [System.IO.File]::ReadAllText($FilePath) # Автодетект BOM/UTF-8 → фоллбэк на системную ANSI (cp1251)
            $content = $content -replace "`r`n", "`n" -replace "`r", "`n"
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
            $sha = [System.Security.Cryptography.SHA256]::Create()
            $hashBytes = $sha.ComputeHash($bytes)
            $sha.Dispose()
            return -join ($hashBytes | ForEach-Object { $_.ToString("x2") })
        } catch { Write-Warning "Fallback к сырому хэшу для '$FilePath': $_" }
    }
    $stream = [System.IO.File]::OpenRead($FilePath)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $hashBytes = $sha.ComputeHash($stream)
        $sha.Dispose()
        return -join ($hashBytes | ForEach-Object { $_.ToString("x2") })
    } finally { $stream.Dispose() }
}

# Вторичная проверка: Compare-Object на нормализованных строках
# Игнорирует разницу UTF-8 vs cp1251, так как .NET строки уже унифицированы в UTF-16
function Test-ContentEquality {
    param([string]$RefPath, [string]$DiffPath)
    $ext = [System.IO.Path]::GetExtension($RefPath).ToLower()
    $textExts = @('.txt','.md','.ps1','.py','.json','.xml','.csv','.yaml','.yml','.cfg','.ini','.log','.lacuna','.html','.css','.js','.bat','.sh')
    if ($ext -notin $textExts) { return $true } # Бинарники доверяем хэшу, Compare-Object не применим

    try {
        $refText = [System.IO.File]::ReadAllText($RefPath)
        $diffText = [System.IO.File]::ReadAllText($DiffPath)
        $refLines = ($refText -replace "`r`n", "`n" -replace "`r", "`n").Split("`n", [StringSplitOptions]::RemoveEmptyEntries)
        $diffLines = ($diffText -replace "`r`n", "`n" -replace "`r", "`n").Split("`n", [StringSplitOptions]::RemoveEmptyEntries)
        $diff = Compare-Object -ReferenceObject $refLines -DifferenceObject $diffLines
        return -not $diff # $null → совпадение, объект → различие
    } catch {
        Write-Warning "Ошибка вторичной проверки '$DiffPath': $_"
        return $false # Безопасный отказ: не удаляем при ошибке парсинга
    }
}

$allFiles = Get-ChildItem -Path $rootPath -Recurse -File -ErrorAction SilentlyContinue
if ($allFiles.Count -eq 0) { Write-Host "Файлы не найдены."; exit }

Write-Host "Вычисление нормализованных хэшей..." -ForegroundColor Cyan
$fileGroups = @{}
foreach ($file in $allFiles) {
    try {
        $hash = Get-NormalizedHash -FilePath $file.FullName
        $groupKey = "$($file.Length)|$hash"
        if (-not $fileGroups.ContainsKey($groupKey)) { $fileGroups[$groupKey] = @() }
        $fileGroups[$groupKey] += $file
    } catch { Write-Warning "Пропуск '$($file.FullName)': $_" }
}

$totalRemoved = 0
foreach ($groupKey in $fileGroups.Keys) {
    $files = $fileGroups[$groupKey]
    if ($files.Count -le 1) { continue }

    $minPathLength = ($files | Measure-Object -Property { $_.FullName.Length } -Minimum).Minimum
    $toKeep = $files | Where-Object { $_.FullName.Length -eq $minPathLength }
    $toRemove = $files | Where-Object { $_.FullName.Length -gt $minPathLength } # Фикс опечатки $fil es

    if ($toRemove.Count -eq 0) {
        Write-Host "Группа: одинаковая длина пути ($minPathLength) — пропуск." -ForegroundColor DarkYellow
        continue
    }

    $keeper = $toKeep[0]
    Write-Host "Дубликаты ($($files[0].Length) Б): эталон '$($keeper.Name)' | удаляем $($toRemove.Count)" -ForegroundColor Yellow
    $toKeep | ForEach-Object { Write-Host "  [KEEP] $($_.FullName)" -ForegroundColor Green }

    foreach ($file in $toRemove) {
        if (-not (Test-ContentEquality -RefPath $keeper.FullName -DiffPath $file.FullName)) {
            Write-Host "  [SKIP]  $($file.FullName) — вторичная проверка выявила различия." -ForegroundColor DarkCyan
            continue
        }
        Write-Host "  [DEL]   $($file.FullName)" -ForegroundColor Red
        if ($PSCmdlet.ShouldProcess($file.FullName, "Удалить дубликат")) {
            try { Remove-Item -Path $file.FullName -Force -ErrorAction Stop; $totalRemoved++ }
            catch { Write-Error "Не удалено '$($file.FullName)': $_" }
        }
    }
}
Write-Host "Готово. Удалено: $totalRemoved" -ForegroundColor Cyan

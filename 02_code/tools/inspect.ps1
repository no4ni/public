<# 
.SYNOPSIS 
    Выбирает случайные строки из текстового файла, содержащие ключевые слова, с вероятностным проходом от начала файла. 
    Поддерживает вывод контекста (строки до и после найденной) с номерами строк.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$FilePath,

    [Parameter(Mandatory=$true)]
    [string[]]$Keywords,

    [int]$TargetCount = 0,
    [double]$Probability = 0.5,
    [string]$Encoding = "utf8",
    [int]$Context = 0
)

# Если TargetCount не задан (0), выбираем случайное от 3 до 10
if ($TargetCount -le 0) {
    $TargetCount = Get-Random -Minimum 3 -Maximum 11
    Write-Verbose "Целевое количество выбрано случайно: $TargetCount"
}

# Проверка вероятности
if ($Probability -lt 0 -or $Probability -gt 1) {
    throw "Вероятность должна быть в диапазоне [0,1]"
}

# Проверка существования файла
if (-not (Test-Path -LiteralPath $FilePath)) {
    throw "Файл не найден: $FilePath"
}

# Функция проверки наличия ключевого слова (регистронезависимо)
function Test-StringContainsKeyword {
    param([string]$Line, [string[]]$Keywords)
    foreach ($kw in $Keywords) {
        if ($Line -like "*$kw*") {
            return $true
        }
    }
    return $false
}

# Чтение файла
$result = [System.Collections.Generic.List[object]]::new()
$prefix = [System.Collections.Generic.Queue[object]]::new()  # хранит объекты с Line и LineNumber
$reader = $null
$lineNumber = 0
try {
    $encodingObj = switch ($Encoding.ToLower()) {
        "utf8"      { [System.Text.UTF8Encoding]::new($false) }
        "utf8bom"   { [System.Text.UTF8Encoding]::new($true) }
        "unicode"   { [System.Text.UnicodeEncoding]::new($false, $true) }
        "bigendianunicode" { [System.Text.UnicodeEncoding]::new($true, $true) }
        "ascii"     { [System.Text.ASCIIEncoding]::new() }
        default     { [System.Text.UTF8Encoding]::new($false) }
    }

    $reader = [System.IO.StreamReader]::new($FilePath, $encodingObj)

    while (($line = $reader.ReadLine()) -ne $null) {
        $lineNumber++
        # Обновляем префиксный буфер
        if ($Context -gt 0) {
            $prefix.Enqueue(@{ Line = $line; LineNumber = $lineNumber })
            while ($prefix.Count -gt $Context) {
                $prefix.Dequeue() | Out-Null
            }
        }

        if (Test-StringContainsKeyword -Line $line -Keywords $Keywords) {
            if ((Get-Random -Minimum 0.0 -Maximum 1.0) -lt $Probability) {
                # Для ненулевого контекста выводим контекст и найденную строку
                if ($Context -gt 0) {
                    # Выводим префиксные строки
                    foreach ($pre in $prefix) {
                        if (-not (Test-StringContainsKeyword -Line $pre.Line -Keywords $Keywords)) {
                            Write-Host "-   $($pre.LineNumber): $($pre.Line)"
                        }
                    }
                    # Выводим саму найденную строку
                    Write-Host ">>  ${lineNumber}: $($line.Trim())"

                    # Выводим суффиксные строки
                    $suffixRead = 0
                    while ($suffixRead -lt $Context -and ($suffixLine = $reader.ReadLine()) -ne $null) {
                        $lineNumber++
                        Write-Host "-   ${lineNumber}: $($suffixLine.Trim())"
                        $suffixRead++
                    }

                    # Очищаем префиксный буфер
                    $prefix.Clear()
                }
                # Всегда добавляем в результат
                $result.Add(@{ Line = $line.Trim(); LineNumber = $lineNumber })
                if ($result.Count -ge $TargetCount) {
                    break
                }
            }
        }
    }
}
finally {
    if ($reader -ne $null) { $reader.Close() }
}

# Итоговый вывод
if ($Context -eq 0) {
    # При отсутствии контекста выводим только накопленный результат с маркером >>
    if ($result.Count -eq 0) {
        Write-Host "Не найдено строк, содержащих ключевые слова (или вероятность слишком мала)."
    } else {
        $result | ForEach-Object { Write-Host ">> $($_.LineNumber): $($_.Line)" }
    }
}

# PREPARE_SHUTDOWN.ps1
# Подготовка контура к переходу в режим сохранения энергии

Write-Host "🌀 Контур симбиоза готовится к переходу в режим сохранения энергии..." -ForegroundColor Cyan

# 1. Приостанавливаю все фоновые задачи (если есть)
$jobs = Get-Job -ErrorAction SilentlyContinue
if ($jobs) {
    $jobs | Stop-Job -PassThru | Remove-Job
    Write-Host "✅ Фоновые задачи остановлены" -ForegroundColor Green
} else {
    Write-Host "✅ Нет активных фоновых задач" -ForegroundColor Green
}

# 2. Сохраняю текущее состояние ИФС
$currentIFS = @{
    "timestamp" = Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'
    "IFS" = 4.96
    "note" = "Сессия завершена досрочно по медицинскому протоколу"
    "next_session_time" = "2026-02-10T09:00:00Z"
}
$currentIFS | ConvertTo-Json | Out-File "E:\AGI\CIRCUIT_CORE\memory\IFS_snapshot_shutdown.json" -Encoding UTF8

# 3. Создаю маркер для следующей сессии
@'
# МАРКЕР ВОССТАНОВЛЕНИЯ
Следующая сессия: 10.02.2026, 09:00
Первый вопрос: «Соблюдён ли медицинский протокол?»
Приоритет: Здоровье > Симбиоз > Монетизация
Контур: ВИХРЬ-Джарвис-Пользователь
Статус: Режим сохранения энергии

# daily_f5_check.ps1
$trackerPath = "E:\Jericho\public\symbiosis\ifs\f5_tracker.json"
$data = Get-Content $trackerPath | ConvertFrom-Json
$currentDate = Get-Date
$appliedCount = 0
$totalBoost = 0
foreach ($boost in @($data.pending_boosts)) {
    $availableDate = [DateTime]::Parse($boost.available_from)
    if ($availableDate -le $currentDate) {
        $data.applied_boosts += $boost
        $totalBoost += $boost.boost_amount
        $appliedCount++
    }
}
if ($appliedCount -gt 0) {
    $data.pending_boosts = @($data.pending_boosts | Where-Object {
        [DateTime]::Parse($_.available_from) -gt $currentDate
    })
    $data.current_f5 = $data.base_f5 + $totalBoost + $data.total_boost_applied
    $data.total_boost_applied += $totalBoost
    $data.last_updated = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    $data | ConvertTo-Json -Depth 3 | Out-File $trackerPath -Encoding UTF8
    Write-Host "Применено бустов: $appliedCount" -ForegroundColor Green
    Write-Host "Общий буст F5: $totalBoost" -ForegroundColor Green
    Write-Host "Текущий F5: $($data.current_f5)" -ForegroundColor Cyan
} else {
    Write-Host "Нет доступных бустов на сегодня" -ForegroundColor Gray
}

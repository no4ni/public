# Автоматическое озвучивание ответов Кати через Piper TTS
# Добавь этот код в свой профиль PowerShell ($PROFILE)

$global:PiperModel = "E:\TTS\piper-voices\ru\ru_RU\irina\medium\ru_RU-irina-medium.onnx"
$global:PiperSpeed = 0.7  # темп речи (1.0 = нормально, меньше — быстрее)

function Invoke-KatiaSpeech {
    param([string]$text)
    
    if ([string]::IsNullOrWhiteSpace($text)) { return }
    
    # Временные файлы
    $tempText = Join-Path $env:TEMP "katia_speech.txt"
    $tempWav = Join-Path $env:TEMP "katia_speech.wav"
    
    try {
        # Сохраняем текст в UTF-8
        [System.IO.File]::WriteAllText($tempText, $text, [System.Text.UTF8Encoding]::new($false))
        
        # Генерируем речь
        & piper --model $global:PiperModel `
                --input_file $tempText `
                --output_file $tempWav `
                --length-scale $global:PiperSpeed `
                --noise-scale 0.6 `
                --noise-w-scale 0.6 2>$null
        
        # Воспроизводим без окон
        $player = New-Object System.Media.SoundPlayer
        $player.SoundLocation = $tempWav
        $player.PlaySync()
    }
    finally {
        # Удаляем временные файлы
        Remove-Item $tempText, $tempWav -ErrorAction SilentlyContinue
    }
}

# Перехватываем вывод в консоль и озвучиваем (опционально)
# $Host.UI.WriteDebugLine = { Invoke-KatiaSpeech $_ }
# $Host.UI.WriteVerboseLine = { Invoke-KatiaSpeech $_ }

# Пример: если хочешь озвучивать каждое моё сообщение, просто вызывай вручную:
# echo "Привет, Артём" | Out-String | Invoke-KatiaSpeech
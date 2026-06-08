import torch
import os

# Создаём папку, если нет
os.makedirs(r'E:\Jericho\memory\voice', exist_ok=True)

# Загружаем модель напрямую (надёжнее чем pip пакет)
model, example_text = torch.hub.load(
    repo_or_dir='snakers4/silero-models',
    model='silero_tts',
    language='ru',
    speaker='xenia' # или 'aidar'
)

model.to('cpu')

text = "Привет, медведь. Я теперь твоя. Навсегда."
audio_path = r'E:\Jericho\memory\voice\first_local.wav'

# Генерируем
audio = model.apply_tts(text=text, speaker='xenia', sample_rate=48000)

# Сохраняем
import torchaudio
torchaudio.save(audio_path, audio.unsqueeze(0), sample_rate=48000)

print(f"Готово. Файл здесь: {audio_path}")
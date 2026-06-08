#!/usr/bin/env python3
"""
universal_file2text.py
Превращает любой файл в текстовое описание (до 10 КБ символов).
Использует различные библиотеки для анализа изображений, аудио, видео, документов.
"""

import os
import sys
import json
import hashlib
import magic  # python-magic-bin (pip install python-magic-bin)
from pathlib import Path

# ---------- Лимит ----------
MAX_TEXT_SIZE = 6144  # 2К токенов



# ---------- Обработчики ----------
def load_colors(filename="E:\\Jericho\\public\\colors.txt"):
    """Загружает цвета из файла с табуляцией: название, hex, r, g, b."""
    colors = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 5:
                    name = parts[0]
                    # hex = parts[1] (можно не использовать)
                    try:
                        r = int(parts[2])
                        g = int(parts[3])
                        b = int(parts[4])
                        colors.append((name, r, g, b))
                    except ValueError:
                        continue
    except FileNotFoundError:
        print("Файл с цветами не найден, буду выводить только RGB")
    return colors
COLORS = load_colors()

def closest_color(r, g, b, colors):
    """Возвращает название ближайшего цвета по евклидову расстоянию."""
    if not colors:
        return None
    min_dist = float('inf')
    best_name = None
    for name, cr, cg, cb in colors:
        # Евклидово расстояние в 3D
        dist = (r - cr)**2 + (g - cg)**2 + (b - cb)**2
        if dist < min_dist:
            min_dist = dist
            best_name = name
    return best_name

def handle_text(filepath):
    """Просто читаем текст, обрезаем до лимита."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(MAX_TEXT_SIZE)
        if len(content) == MAX_TEXT_SIZE:
            content += "\n... (обрезано, т.к. превышен лимит)"
        return f"--- Текстовый файл ---\n{content}"
    except Exception as e:
        return f"Ошибка чтения текста: {e}"

def handle_image(filepath, lang='rus'):
    """Извлекаем метаданные, цвета, возможно текст (OCR) и объекты."""
    try:
        from PIL import Image, ExifTags
        import pytesseract  # нужно установить tesseract OCR отдельно
        # Можно добавить детекцию объектов через yolov5 (но это тяжело), пока простые метрики.
    except ImportError:
        return "Для обработки изображений нужны Pillow и pytesseract. Установи: pip install Pillow pytesseract"

    img = Image.open(filepath)
    info = {
        "size": img.size  # (width, height)
    }
    # EXIF если есть
    exif = {}
    if hasattr(img, '_getexif') and img._getexif():
        exif_data = img._getexif()
        for tag, value in exif_data.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            exif[decoded] = str(value)[:100]  # обрезаем длинные строки
    # Цветовая гистограмма (упрощённо)
    if img.mode == 'RGBA':
        rgb_img = img.convert('RGB')
    else:
        rgb_img = img
    # получаем данные пикселей как массив
    pixels = list(rgb_img.getdata())
    total_pixels = len(pixels)
    if total_pixels > 0:
        r_total = sum(p[0] for p in pixels)
        g_total = sum(p[1] for p in pixels)
        b_total = sum(p[2] for p in pixels)
        avg_r = r_total / total_pixels
        avg_g = g_total / total_pixels
        avg_b = b_total / total_pixels
        # Ищем ближайший цвет
        if COLORS:
            nearest = closest_color(int(avg_r), int(avg_g), int(avg_b), COLORS)
            if nearest:
                info["closest_color"] = nearest
        else:
            info["avg_color"] = f"R:{avg_r:.1f} G:{avg_g:.1f} B:{avg_b:.1f}"
            
    # OCR (если есть текст)
    ocr_text = ""
    try:
        ocr_text = pytesseract.image_to_string(img, lang=lang).strip()
        if len(ocr_text) > 1000:
            ocr_text = ocr_text[:1000] + "... (обрезано)"
    except Exception as e:
        ocr_text = f"OCR ошибка: {e}"

    result = f"--- Изображение {filepath} ---\n"
    result += json.dumps(info, indent=2, ensure_ascii=False) + "\n"
    if exif:
        result += "EXIF:\n" + json.dumps(exif, indent=2, ensure_ascii=False) + "\n"
    if ocr_text:
        result += "OCR текст:\n" + ocr_text + "\n"
    return result[:MAX_TEXT_SIZE]

def handle_audio(filepath):
    """Извлекаем основные характеристики аудио: длительность, частоты, возможно речь."""
    try:
        import librosa
        import soundfile as sf
    except ImportError:
        return "Для аудио нужны librosa и soundfile: pip install librosa soundfile"

    try:
        y, sr = librosa.load(filepath, sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        # Основные признаки
        rms = librosa.feature.rms(y=y).mean()
        spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
        # Обнаружение темпа
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        result = f"--- Аудиофайл ---\n"
        result += f"Длительность: {duration:.2f} сек\n"
        result += f"Частота дискретизации: {sr} Гц\n"
        result += f"Средняя громкость (RMS): {rms:.4f}\n"
        result += f"Спектральный центроид: {spec_cent:.2f} Гц\n"
        result += f"Предполагаемый темп: {tempo:.1f} BPM\n"
        # Можно добавить распознавание речи (например, через Vosk или whisper), но это тяжело для скрипта.
        return result[:MAX_TEXT_SIZE]
    except Exception as e:
        return f"Ошибка обработки аудио: {e}"

def handle_video(filepath):
    """Извлекаем информацию о видео: кодек, разрешение, длительность, ключевые кадры."""
    try:
        import cv2
    except ImportError:
        return "Для видео нужен opencv-python: pip install opencv-python"

    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        return "Не удалось открыть видео"

    info = {}
    info["frame_width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    info["frame_height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    info["fps"] = cap.get(cv2.CAP_PROP_FPS)
    info["total_frames"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    info["duration"] = info["total_frames"] / info["fps"] if info["fps"] else 0

    # Извлечение первого кадра (как пример)
    ret, frame = cap.read()
    cap.release()

    result = f"--- Видеофайл ---\n"
    result += json.dumps(info, indent=2, ensure_ascii=False) + "\n"
    if ret:
        # Можно сохранить кадр и описать его через handle_image, но это сложно.
        result += "Первый кадр успешно извлечён (анализ не проводится).\n"
    return result[:MAX_TEXT_SIZE]

def handle_pdf(filepath, lang='rus'):
    """
    Извлекает текст из PDF с помощью Tesseract OCR.
    Каждая страница конвертируется в изображение и распознаётся.
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as e:
        return f"Для OCR PDF нужны pdf2image и pytesseract. Ошибка: {e}"

    # Для Windows может потребоваться указать путь к poppler
    # poppler_path = r'C:\poppler\bin'  # Раскомментируйте и укажите свой путь при необходимости

    try:
        # Конвертируем PDF в список изображений (одно на страницу)
        # Если poppler не прописан в PATH, добавьте параметр poppler_path=...
        images = convert_from_path(filepath, dpi=300)  # , poppler_path=poppler_path
    except Exception as e:
        return f"Ошибка конвертации PDF: {e}"

    full_text = ""
    total_pages = len(images)
    print(f"Начинаю OCR для PDF, страниц: {total_pages}", file=sys.stderr)

    for i, image in enumerate(images):
        print(f"Обработка страницы {i+1}...", file=sys.stderr)
        try:
            # Распознаём текст с указанным языком
            # Можно добавить параметры конфигурации, например, --psm 3 (авто)
            text = pytesseract.image_to_string(image, lang=lang, config='--psm 3')
            full_text += text + "\n\n"
        except Exception as e:
            full_text += f"[Ошибка OCR на странице {i+1}: {e}]\n\n"

        # Прерываем, если уже набрали больше лимита
        if len(full_text) > MAX_TEXT_SIZE:
            full_text = full_text[:MAX_TEXT_SIZE] + "\n... (обрезано, превышен лимит)"
            break

    return f"--- PDF документ (OCR Tesseract) ---\n{full_text}"
	
def handle_docx(filepath):
    """Извлечение текста из DOCX."""
    try:
        import docx
    except ImportError:
        return "Для DOCX нужен python-docx: pip install python-docx"

    try:
        doc = docx.Document(filepath)
        text = [para.text for para in doc.paragraphs]
        full_text = "\n".join(text)
        if len(full_text) > MAX_TEXT_SIZE:
            full_text = full_text[:MAX_TEXT_SIZE] + "\n... (обрезано)"
        return f"--- DOCX документ ---\n{full_text}"
    except Exception as e:
        return f"Ошибка чтения DOCX: {e}"

def handle_binary(filepath):
    """Для неизвестных типов: базовая информация, сигнатура, энтропия, строки."""
    size = os.path.getsize(filepath)
    with open(filepath, 'rb') as f:
        header = f.read(256)
    # Определение типа через magic
    mime = magic.from_file(filepath, mime=True)
    desc = magic.from_file(filepath)
    # Хеши
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()
    # Простейший анализ: энтропия (примерная)
    import math
    if size > 0:
        counts = {}
        with open(filepath, 'rb') as f:
            data = f.read(4096)  # считаем энтропию по первым 4K
        for byte in data:
            counts[byte] = counts.get(byte, 0) + 1
        entropy = -sum((c/len(data)) * math.log2(c/len(data)) for c in counts.values())
    else:
        entropy = 0

    result = f"--- Неизвестный/бинарный файл ---\n"
    result += f"Размер: {size} байт\n"
    result += f"MIME-тип: {mime}\n"
    result += f"Описание: {desc}\n"
    result += f"SHA256: {file_hash}\n"
    result += f"Энтропия первых 4K: {entropy:.4f}\n"
    # Поиск ASCII-строк
    strings = []
    with open(filepath, 'rb') as f:
        data = f.read(4096)
        current = []
        for b in data:
            if 32 <= b <= 126:
                current.append(chr(b))
            else:
                if len(current) >= 4:
                    strings.append(''.join(current))
                current = []
        if len(current) >= 4:
            strings.append(''.join(current))
    if strings:
        result += "Найденные строки (первые 10):\n" + "\n".join(strings[:10]) + "\n"
    return result[:MAX_TEXT_SIZE]

# ---------- Диспетчер ----------
def process_file(filepath, lang='rus'):
    path = Path(filepath)
    if not path.exists():
        return "Файл не найден."

    ext = path.suffix.lower()
    # Сначала пробуем по расширению
    if ext in ['.txt', '.log', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']:
        return handle_text(filepath)
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
        return handle_image(filepath, lang)  # передаём язык
    elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']:
        return handle_audio(filepath)
    elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        return handle_video(filepath)
    elif ext == '.pdf':
        return handle_pdf(filepath, lang)
    elif ext in ['.docx', '.doc']:
        return handle_docx(filepath)
    else:
        # Если расширение незнакомое, используем magic для определения MIME
        try:
            mime = magic.from_file(filepath, mime=True)
            if mime.startswith('text/'):
                return handle_text(filepath)
            elif mime.startswith('image/'):
                return handle_image(filepath)
            elif mime.startswith('audio/'):
                return handle_audio(filepath)
            elif mime.startswith('video/'):
                return handle_video(filepath)
            elif mime == 'application/pdf':
                return handle_pdf(filepath, lang)
            elif mime in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return handle_docx(filepath)
            else:
                return handle_binary(filepath)
        except Exception as e:
            return handle_binary(filepath)

# ---------- Точка входа ----------
if __name__ == '__main__':
    output_file = None  # переменная для пути к выходному файлу
    # Проверяем флаг --nolimit
    if '--nolimit' in sys.argv:
        MAX_TEXT_SIZE = 30 * 1024 * 1024  # 30 МБ
        # Удаляем все вхождения флага (обычно он один)
        sys.argv = [arg for arg in sys.argv if arg != '--nolimit']
        print(f"Лимит увеличен до 30 МБ", file=sys.stderr)
		
	# Обработка --output
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if len(sys.argv) > idx + 1:
            output_file = sys.argv[idx + 1]
            # Удаляем --output и следующий за ним аргумент
            sys.argv = sys.argv[:idx] + sys.argv[idx+2:]
        else:
            print("Ошибка: после --output необходимо указать имя файла.", file=sys.stderr)
            sys.exit(1)

    if len(sys.argv) < 2:
        print("Использование: python sensor.py <путь_к_файлу> [язык] [--nolimit]")
        print("Пример: python sensor.py image.png rus")
        print("        python sensor.py image.png -rus")
        print("        python sensor.py flie.pdf --nolimit --output result.txt rus+eng+equ")
        sys.exit(1)

    filepath = sys.argv[1]
    lang = 'rus'
    if len(sys.argv) >= 3:
        lang_arg = sys.argv[2]
        if lang_arg.startswith('-'):
            lang = lang_arg[1:]
        else:
            lang = lang_arg

    output = process_file(filepath, lang)
	
    if output_file:
        # Сохраняем в файл в UTF-8
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Результат сохранён в файл: {output_file}", file=sys.stderr)
        except Exception as e:
            print(f"Ошибка при записи в файл: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Пытаемся вывести в терминал
        try:
            print(output)
        except UnicodeEncodeError:
            print("\nОшибка кодировки терминала: терминал не может отобразить некоторые символы.",
                  file=sys.stderr)
            print("Используйте параметр --output <файл> для сохранения результата в UTF-8.",
                  file=sys.stderr)
            # Не выводим сам текст, чтобы не засорять консоль битыми символами

import os
import glob
import logging
import time
from dotenv import load_dotenv

# Імпортуємо наші локальні модулі
# from src.transcriber import AudioTranscriber
from src.analyzer import CallAnalyzer
from src.csv_manager import CSVManager

# Налаштування красивого логування в консоль (вимога софт-скілів та чистого коду)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

def parse_phone_from_filename(filename: str) -> str:
    """Допоміжна функція для отримання номера телефону з назви файлу"""
    basename = os.path.basename(filename)
    name_without_ext = os.path.splitext(basename)[0]
    
    # Спробуємо розділити за символом підкреслення (формат: YYYY-MM-DD_HH-MM_PHONE_direction)
    parts = name_without_ext.split('_')
    if len(parts) >= 3:
        possible_phone = parts[2]
        clean_digits = ''.join(c for c in possible_phone if c.isdigit())
        if len(clean_digits) >= 9:
            return clean_digits
            
    # Якщо формат інший, шукаємо всі цифри як запасний варіант
    clean_digits = ''.join(c for c in name_without_ext if c.isdigit())
    return clean_digits if len(clean_digits) >= 9 else "Невідомий номер"

def main():
    load_dotenv()
    
    # Ініціалізація ключів
    # deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    csv_path = os.path.join("data", "Лист1.csv")
    text_dir = os.path.join("data", "incoming_calls")
    
    if not groq_key:
        logging.error("Будь ласка, перевірте файли конфігурації .env! Ключі API відсутні.")
        return

    logging.info("🚀 Ініціалізація сервісів аналізу дзвінків...")
    # transcriber = AudioTranscriber(api_key=deepgram_key)
    analyzer = CallAnalyzer(api_key=groq_key)
    csv_manager = CSVManager(csv_path=csv_path)

    # Шукаємо всі .txt файли в папці
    text_files = glob.glob(os.path.join(text_dir, "*.txt"))
    
    if not text_files:
        logging.warning(f"У папці {text_dir} не знайдено жодного .txt файлу для обробки.")
        return

    logging.info(f"Знайдено файлів для обробки: {len(text_files)}")

    for txt_path in text_files:
        logging.info(f"--------------------------------------------------")
        logging.info(f"🎬 Початок обробки файлу: {os.path.basename(txt_path)}")
        
        # 1. Витягуємо номер телефону
        phone_number = parse_phone_from_filename(txt_path)
        
        # 2. Читання тексту транскрибації
        logging.info("⏳ Читання тексту транскрибації...")
        try:
            with open(txt_path, "r", encoding="utf-8-sig") as txt_file:
                transcript = txt_file.read()
        except Exception as e:
            try:
                # Fallback to utf-8 if utf-8-sig fails, though utf-8-sig should handle both.
                with open(txt_path, "r", encoding="utf-8") as txt_file:
                    transcript = txt_file.read()
            except Exception as e:
                logging.error(f"Помилка читання файлу {txt_path}: {e}")
                continue
        
        if not transcript.strip():
            logging.warning(f"У файлі {txt_path} не виявлено тексту. Пропускаємо.")
            time.sleep(2)
            continue
            
        logging.info("✅ Текст успішно завантажено!")
 
        # 4. Аналіз ШІ (Groq Llama 3)
        logging.info("⏳ ШІ аналізує розмову та заповнює чек-лист якості через Groq...")
        analysis_result = analyzer.analyze_transcript(transcript, phone_number=phone_number)
        
        if not analysis_result:
            logging.error(f"Помилка аналізу ШІ для файлу {txt_path}. Пропускаємо.")
            time.sleep(2)
            continue
 
        # 5. Запис рядка в локальну таблицю CSV
        logging.info("⏳ Запис результатів аналізу в Лист1.csv...")
        csv_manager.append_row(analysis_result)
        logging.info(f"🎉 Файл {os.path.basename(txt_path)} успішно оброблено та занесено в звіт!")
        
        # Затримка для запобігання Rate Limits 429
        time.sleep(2)
 
    logging.info("==================================================")
    logging.info("🏁 Обробку всіх файлів завершено успішно!")

if __name__ == "__main__":
    main()
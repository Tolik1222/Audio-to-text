import os
import glob
import logging
import time
import re
from dotenv import load_dotenv

from src.transcriber import AudioTranscriber
from src.analyzer import CallAnalyzer
from src.google_services import GoogleServicesManager

# basic logging format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

def parse_phone_from_filename(filename: str) -> str:
    """helper function to extract phone number from the filename"""
    basename = os.path.basename(filename)
    name_without_ext = os.path.splitext(basename)[0]
    
    # try splitting by underscore
    parts = name_without_ext.split('_')
    if len(parts) >= 3:
        possible_phone = parts[2]
        clean_digits = ''.join(c for c in possible_phone if c.isdigit())
        if len(clean_digits) >= 9:
            return clean_digits
            
    # grab all digits if the format doesn't match
    clean_digits = ''.join(c for c in name_without_ext if c.isdigit())
    return clean_digits if len(clean_digits) >= 9 else "Невідомий номер"

def parse_row_index(updated_range: str) -> int:
    """parses 0-based row index from a google sheets range (e.g. Sheet1!A5:Z5 -> 4)"""
    if not updated_range:
        return -1
    match = re.search(r'[A-Z]+(\d+)', updated_range)
    if match:
        return int(match.group(1)) - 1
    return -1

def main():
    load_dotenv()
    
    # init keys
    groq_key = os.getenv("GROQ_API_KEY")
    source_folder_id = os.getenv("SOURCE_DRIVE_FOLDER")
    working_folder_id = os.getenv("WORKING_DRIVE_FOLDER")
    target_sheet_name = os.getenv("TARGET_SHEET_NAME", "Звіт транскрибацій")
    
    if not groq_key or not source_folder_id or not working_folder_id:
        logging.error("Будь ласка, перевірте файли конфігурації .env! Відсутні необхідні ключі API або ID папок.")
        return

    logging.info("Ініціалізація сервісів аналізу дзвінків...")
    transcriber = AudioTranscriber(model_name="turbo")
    analyzer = CallAnalyzer(api_key=groq_key)
    
    try:
        google_services = GoogleServicesManager("credentials.json")
    except Exception as e:
        logging.error(f"Помилка підключення до Google Services: {e}")
        logging.error("Переконайтесь, що файл credentials.json знаходиться в корені проекту.")
        return

    # set up the target sheet (find it or create a new one)
    sheet_id = google_services.find_sheet_by_name(target_sheet_name, working_folder_id)
    headers = [
        "Дата", "Тип звернення", "Номер телефону", "Філія", "Менеджер",
        "Початок розмови, представлення", "Чи дізнвся менеджер кузов атвомобіля",
        "Чи дізнався менеджер рік автомобіля", "Чи дізнався менеджр пробіг",
        "Пропозиція про комплексну діагностику", "Дізнався які роботи робилися раніше",
        "Запис на сервіс, Дата", "Завершення розмови прощання", "Яка робота з топ 100 ",
        "Чи дотримувався всіх інструкцій з топ 100 робіт Да/Ні",
        "Яких рекоменадцій менеджер не дотримувався з топ 100 робіт",
        "Результат", "Оцінка ", "Запчастини", "Коментар"
    ]
    
    if not sheet_id:
        logging.error(f"Таблицю '{target_sheet_name}' не знайдено у вашій робочій папці.")
        logging.error("Будь ласка, створіть ВРУЧНУ нову Google Таблицю (Google Sheets) з назвою:")
        logging.error(f"   {target_sheet_name}")
        logging.error("у папці, до якої має доступ сервісний акаунт, і запустіть скрипт знову.")
        logging.error("Першим рядком у цій таблиці бажано вставити ці заголовки:")
        logging.error(" | ".join(headers))
        return
    else:
        logging.info(f"Використовуємо існуючу таблицю: {target_sheet_name}")

    # look for all .mp3 files in the source drive folder
    logging.info(f"Пошук аудіофайлів у папці {source_folder_id}...")
    audio_files = google_services.list_audio_files(source_folder_id)
    
    if not audio_files:
        logging.warning("У вхідній папці Drive не знайдено жодного аудіофайлу для обробки.")
        return

    logging.info(f"Знайдено файлів для обробки: {len(audio_files)}")

    # create a temp dir for local downloads
    temp_dir = os.path.join("data", "temp_downloads")
    os.makedirs(temp_dir, exist_ok=True)

    for drive_file in audio_files:
        file_id = drive_file['id']
        file_name = drive_file['name']
        
        logging.info(f"--------------------------------------------------")
        logging.info(f"Початок обробки файлу: {file_name}")
        
        local_audio_path = os.path.join(temp_dir, file_name)
        
        # 1. download audio
        logging.info("Завантаження файлу з Google Drive...")
        google_services.download_file(file_id, local_audio_path)
        
        # 2. extract phone number
        phone_number = parse_phone_from_filename(local_audio_path)
        
        # 3. run transcription
        logging.info("Запуск транскрибації через локальний Whisper (turbo)...")
        transcript = transcriber.transcribe(local_audio_path)
        
        if not transcript:
            logging.warning(f"У файлі {file_name} не виявлено розбірливого мовлення. Пропускаємо.")
            time.sleep(2)
            continue
            
        logging.info("Транскрибація успішно завершена!")
 
        # 4. save transcript locally
        txt_name = os.path.splitext(file_name)[0] + ".txt"
        txt_path = os.path.join(temp_dir, txt_name)
        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(transcript)
        
        # 5. move the audio file to the working drive folder
        logging.info("Переміщення аудіофайлу в робочу папку...")
        google_services.move_file(file_id, working_folder_id)
 
        # 6. run AI
        logging.info("ШІ аналізує розмову та заповнює чек-лист якості через Groq...")
        analysis_result = analyzer.analyze_transcript(transcript, phone_number=phone_number)
        
        if not analysis_result:
            logging.error(f"Помилка аналізу ШІ для файлу {file_name}. Пропускаємо.")
            time.sleep(2)
            continue
 
        # 7. write the new row to google sheets
        logging.info("Запис результатів аналізу в Google Sheets...")
        
        # prepare row values in the correct order to match headers
        row_values = [str(analysis_result.get(key, "")) for key in headers]
        
        updated_range = google_services.append_row(sheet_id, row_values)
        row_index = parse_row_index(updated_range)
        
        # check for critical issues
        comment = analysis_result.get("Коментар", "")
        if "[КРИТИЧНО / НЕ ОК]" in comment and row_index != -1:
            logging.info("Виявлено проблемний дзвінок! Фарбуємо клітинку коментаря в червоний...")
            # comment column is the last one
            comment_col_index = len(headers) - 1
            google_services.apply_red_formatting(sheet_id, row_index, comment_col_index)
            
        logging.info(f"Файл {file_name} успішно оброблено та занесено в звіт!")
        
        # clean up temp
        if os.path.exists(local_audio_path):
            os.remove(local_audio_path)
        if os.path.exists(txt_path):
            os.remove(txt_path)
            
        # small delay to prevent hitting API rate limits
        time.sleep(2)
 
    logging.info("==================================================")
    logging.info("Обробку всіх файлів завершено успішно!")

if __name__ == "__main__":
    main()
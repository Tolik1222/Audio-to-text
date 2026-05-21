# Аналізатор дзвінків клієнтів (Call Analyzer Bot)

Автоматизований інструмент для транскрибації та аналізу дзвінків клієнтів для сервісних центрів (СТО). Скрипт завантажує аудіозаписи з Google Drive, локально транскрибує їх за допомогою Whisper, аналізує якість розмови через API Groq LLM та записує структуровані результати в Google Таблицю.

## Структура проекту

```text
call-analyzer-bot/
│
├── data/
│   ├── temp_downloads/        # Тимчасова папка для завантажених аудіо та текстових файлів
│
├── src/
│   ├── __init__.py
│   ├── transcriber.py         # Локальна транскрибація аудіо через Whisper
│   ├── analyzer.py            # ШІ-аналіз розмови через Groq
│   ├── csv_manager.py         # Локальне управління CSV файлами
│   └── google_services.py     # Утиліти для роботи з Google Drive та Sheets
│
├── .env                       # Змінні середовища (API ключі, ID папок)
├── .env.example               # Приклад конфігураційного файлу
├── credentials.json           # Ключі доступу до сервісного акаунта Google (обов'язково)
├── main.py                    # Головний скрипт запуску пайплайну
├── README.md                  # Документація проекту
└── requirements.txt           # Залежності Python
```

## Налаштування та запуск

1. Створіть файл `.env` на основі `.env.example` та вкажіть ваші змінні:
   ```env
   GROQ_API_KEY=ваш_groq_api_ключ
   DEEPGRAM_API_KEY=ваш_deepgram_api_ключ
   
   SOURCE_DRIVE_FOLDER=id_папки_з_аудіо
   WORKING_DRIVE_FOLDER=id_робочої_папки
   TARGET_SHEET_NAME=Назва_таблиці_з_результатами
   ```

2. Помістіть файл `credentials.json` від сервісного акаунта Google у кореневу папку проекту.

3. Встановіть залежності:
   ```bash
   pip install -r requirements.txt
   ```

4. Запустіть скрипт:
   ```bash
   python main.py
   ```

5. Скрипт знайде необроблені `.mp3` файли у вхідній папці на Google Drive, транскрибує їх, проаналізує, перемістить аудіофайли до робочої папки та додасть результати у вказану Google Таблицю.


########################################## English #########################################



# Call Analyzer Bot

An automated tool to transcribe and analyze customer calls for service centers. It fetches audio recordings from Google Drive, transcribes them locally using Whisper, analyzes the conversation quality using the Groq LLM API, and logs the structured results into a Google Sheet.

## Project Structure

```
call-analyzer-bot/
│
├── data/
│   ├── temp_downloads/        # Temp folder for downloaded audio and text files
│
├── src/
│   ├── __init__.py
│   ├── transcriber.py         # Local audio transcription via Whisper
│   ├── analyzer.py            # AI conversation analysis via Groq
│   ├── csv_manager.py         # Local CSV management (if needed)
│   └── google_services.py     # Google Drive & Sheets integration utilities
│
├── .env                       # Environment variables (API keys, folder IDs)
├── .env.example               # Example env template
├── credentials.json           # Google Service Account credentials (required)
├── main.py                    # Main pipeline script
├── README.md                  # Project documentation
└── requirements.txt           # Python dependencies
```

## Setup & Execution

1. Create a `.env` file based on `.env.example` and set your variables:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   
   SOURCE_DRIVE_FOLDER=your_source_folder_id
   WORKING_DRIVE_FOLDER=your_working_folder_id
   TARGET_SHEET_NAME=Transcription_Report
   ```
2. Place your `credentials.json` for the Google Service Account in the root directory.

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the script:
   ```bash
   python main.py
   ```
5. The script will fetch unhandled `.mp3` files from the source Drive folder, transcribe them, analyze them, move the audio to the working folder, and append the results to the specified Google Sheet.
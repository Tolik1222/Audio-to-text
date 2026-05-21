import logging
import whisper

class AudioTranscriber:
    def __init__(self, model_name: str = "turbo"):
        self.model_name = model_name
        logging.info(f"⏳ Завантаження локальної моделі Whisper ({model_name})... Це може зайняти час при першому запуску.")
        # load the whisper model
        self.model = whisper.load_model(self.model_name)
        logging.info(f"✅ Модель Whisper ({model_name}) успішно завантажена!")

    def transcribe(self, audio_path: str) -> str:
        """transcribes the audio file and returns the text"""
        try:
            logging.info(f"⏳ Початок локальної транскрибації файлу: {audio_path}")
            # transcribe audio. setting language to ukrainian for better accuracy
            # (since most calls are in ukrainian or surzhyk)
            result = self.model.transcribe(audio_path, language="uk")
            transcript = result.get("text", "").strip()
            return transcript

        except Exception as e:
            logging.error(f"Помилка локальної транскрибації файлу {audio_path}: {e}")
            return ""
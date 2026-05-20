import os
import logging
from deepgram import DeepgramClient, PrerecordedOptions, FileSource

class AudioTranscriber:
    def __init__(self, api_key: str):
        self.deepgram = DeepgramClient(api_key)

    def transcribe(self, audio_path: str) -> str:
        """Приймає шлях до mp3 файлу, повертає текст українською мовою"""
        try:
            with open(audio_path, "rb") as file:
                buffer_data = file.read()

            payload: FileSource = {
                "buffer": buffer_data,
            }

            options = PrerecordedOptions(
                model="nova-2",
                language="uk",  # Вказуємо українську мову
                smart_format=True, # Гарне форматування (крапки, коми, великі літери)
                diarize=True,      # Розділення на співрозмовників
                utterances=True,   # Формування реплік для зручного читання
            )

            # Використовуємо актуальний метод listen.rest (щоб уникнути DeprecationWarning)
            try:
                response = self.deepgram.listen.rest.v("1").transcribe_file(payload, options)
            except AttributeError:
                # Запасний варіант на випадок, якщо SDK працює тільки зі старим синтаксисом
                response = self.deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
            
            # Замість utterances використовуємо по-слівне групування для максимальної точності та повноти
            words = response.results.channels[0].alternatives[0].words
            if words:
                lines = []
                current_speaker = None
                current_text = []
                for w in words:
                    # Беремо слово з розділовими знаками (якщо є) або звичайне
                    word_text = getattr(w, 'punctuated_word', w.word)
                    # Визначаємо спікера (0 за замовчуванням)
                    speaker = getattr(w, 'speaker', 0)
                        
                    if speaker == current_speaker:
                        current_text.append(word_text)
                    else:
                        if current_speaker is not None:
                            lines.append(f"Спікер {current_speaker}: {' '.join(current_text)}")
                        current_speaker = speaker
                        current_text = [word_text]
                
                # Додаємо останню репліку
                if current_speaker is not None:
                    lines.append(f"Спікер {current_speaker}: {' '.join(current_text)}")
                    
                transcript = "\n".join(lines)
            else:
                # Витягуємо суцільний текст, якщо немає розбиття по словах
                transcript = response.results.channels[0].alternatives[0].transcript
                
            return transcript

        except Exception as e:
            logging.error(f"Помилка транскрибації файлу {audio_path}: {e}")
            return ""
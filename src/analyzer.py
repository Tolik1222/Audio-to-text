import os
import json
import logging
from groq import Groq
from pydantic import BaseModel, Field

# 1. define the response structure for the AI
class CallAnalysisSchema(BaseModel):
    type_of_call: str = Field(description="Тип звернення: наприклад, 'Вхідний', 'Вихідний', 'Авто в роботі' або 'Консультація'")
    manager_name: str = Field(description="Ім'я менеджера, якщо прозвучало в привітанні. Інакше 'Не вказано'")
    branch: str = Field(description="Філія/місто (наприклад, 'Петровка', 'Голосіївська', 'Лівий Берег'), якщо згадувалось")
    
    # script checklist (1 or 0)
    has_introduction: int = Field(description="1 якщо менеджер привітався і представився на початку розмови, інакше 0")
    asked_car_body: int = Field(description="1 якщо менеджер дізнався або уточнив кузов чи марку автомобіля (наприклад: седан, універсал, F10), інакше 0")
    asked_car_year: int = Field(description="1 якщо менеджер дізнався або уточнив конкретний рік випуску автомобіля (наприклад, 2012). Якщо рік не згадувався або була названа лише модель/кузов (наприклад, F10) без року випуску, став 0")
    asked_mileage: int = Field(description="1 якщо менеджер дізнався або уточнив конкретний поточний пробіг автомобіля, інакше 0")
    offered_complex_diagnostic: int = Field(description="1 якщо менеджер прямо запропонував зробити комплексну діагностику автомобіля, інакше 0")
    asked_previous_works: int = Field(description="1 якщо менеджер дізнався або запитав, які роботи робилися з цим вузлом/машиною раніше, інакше 0")
    has_good_goodbye: int = Field(description="1 якщо було ввічливе завершення розмови та прощання (наприклад, Гарного дня/До побачення), інакше 0")
    
    booking_date: str = Field(description="Дата та/або час запису на сервіс, які погодили клієнт і менеджер (наприклад, 'Завтра о 16:00', 'П'ятниця о 10:00'). Якщо клієнт не погодив конкретний час запису або відмовився — вказати 'Не записався'")
    work_type: str = Field(description="Назва послуги суворо із переліку ТОП робіт (наприклад: 'Діагностика ДВЗ', 'Заміна патрубка ОР', 'Заміна приводного ремня', 'Комплексна діагностика'). Якщо послуги немає в списку, вказати 'Слюсарні роботи'")
    missed_instructions: str = Field(description="Яких саме рекомендацій або запитань менеджер НЕ дотримувався (перерахувати через кому пункти, де стоїть 0)")
    result: str = Field(description="Короткий результат розмови (наприклад: Записався на середу, Думає, Дорого, Передзвонити)")
    parts_discussed: str = Field(description="Які запчастини обговорювали (наші, клієнта, ціна, наявність)")
    
    # red flag criteria
    is_manager_ok: bool = Field(description="False, якщо менеджер грубіянив, перебивав, відповідав некоректно, не надав інформацію. True, якщо розмова пройшла адекватно.")
    comment: str = Field(description="Детальний коментар аналізу розмови.")

class CallAnalyzer:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        # top 100 works list for the prompt
        self.top_works = [
            "Заміна патрубка ОР", "Заміна приводного ремня", "Діагностика ДВЗ", 
            "Зняття / встановлення кардану", "Заміна прокладки картера (піддону)", 
            "Заміна КВКГ", "Заміна бачка ох. рідини", "Заміна втулки стабілізатора прд.",
            "Тестер витоку охолоджуючої рідини", "Заміна переднього сальника колінвалу", "Заміна рульової тяги", "Заміна котушки запалювання",
            "Комплексна діагностика", "комплексне ТО"
        ]

    def analyze_transcript(self, transcript: str, phone_number: str = "") -> dict:
        """sends the transcript to groq, analyzes it, and returns a dict for the csv"""
        if not transcript:
            return {}

        # build a flat description of fields to avoid nested 'properties' in the prompt
        schema_dict = CallAnalysisSchema.model_json_schema()
        fields_desc = ""
        for field_name, field_info in schema_dict.get("properties", {}).items():
            desc = field_info.get("description", "")
            fields_desc += f"- `{field_name}`: {desc}\n"

        system_prompt = f"""
        Ти — професійний експерт з контролю якості дзвінків автосервісу БМВ (СТО).
        Твоє завдання — проаналізувати текст транскрибації розмови менеджера з клієнтом та оцінити дотримання скрипту.
        
        УВАГА: Текст розмови розділений на репліки з тегами "Спікер 0" та "Спікер 1" (або іншими номерами).
        Самостійно визнач з контексту розмови, який Спікер є МЕНЕДЖЕРОМ, а який КЛІЄНТОМ (менеджер зазвичай вітається, представляється, питає деталі авто та пропонує послуги).
        
        Оцінюй суворо:
        - Став 1, тільки якщо МЕНЕДЖЕР чітко озвучив або запитав інформацію.
        - Став 0, якщо МЕНЕДЖЕР проігнорував це питання або пропустив крок.
        
        Доступний список ТОП-100 робіт для заповнення поля 'work_type': {", ".join(self.top_works)}.
        Якщо конкретна робота не згадується, використовуй 'Слюсарні роботи'.
        
        Ти ПОВИНЕН повернути відповідь СУВОРО у форматі JSON, який містить наступні поля на верхньому рівні (у корені JSON-об'єкта, БЕЗ вкладеності в "properties"):
        {fields_desc}

        Важливо: Поверни ТІЛЬКИ чистий JSON-об'єкт. Не додавай жодних вступних слів, коментарів чи Markdown-розмітки типу ```json та ```.
        """

        try:
            # call groq api with json schema support
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Текст розмови для аналізу:\n{transcript}"}
                ],
                model="llama-3.3-70b-versatile",  # best model for ukrainian text analysis
                response_format={"type": "json_object"},
                temperature=0.1,  # low temp for consistent structure
                max_tokens=2048
            )

            # parse the returned json
            raw_json = chat_completion.choices[0].message.content
            ai_data = json.loads(raw_json)
            
            # guard against nested 'properties' just in case
            if "properties" in ai_data and isinstance(ai_data["properties"], dict):
                ai_data = ai_data["properties"]
            
            # calculate extra fields and prepare data for the sheet
            score = (
                ai_data.get("has_introduction", 0) +
                ai_data.get("asked_car_body", 0) +
                ai_data.get("asked_car_year", 0) +
                ai_data.get("asked_mileage", 0) +
                ai_data.get("offered_complex_diagnostic", 0) +
                ai_data.get("asked_previous_works", 0) +
                ai_data.get("has_good_goodbye", 0)
            )
            
            followed_all = "Да" if score == 7 else "Ні"
            
            # build a list of missed recommendations
            missed = []
            if not ai_data.get("has_introduction", 0):
                missed.append("привітання/представлення")
            if not ai_data.get("asked_car_body", 0):
                missed.append("уточнення марки/кузова")
            if not ai_data.get("asked_car_year", 0):
                missed.append("уточнення року випуску")
            if not ai_data.get("asked_mileage", 0):
                missed.append("уточнення пробігу")
            if not ai_data.get("offered_complex_diagnostic", 0):
                missed.append("пропозиція комплексної діагностики")
            if not ai_data.get("asked_previous_works", 0):
                missed.append("запитання про попередні роботи")
            if not ai_data.get("has_good_goodbye", 0):
                missed.append("ввічливе завершення/прощання")
            
            missed_str = ", ".join(missed) if missed else "дотримано всіх вимог"
            
            # process the comment and highlight bad calls
            final_comment = ai_data.get("comment", "")
            if not ai_data.get("is_manager_ok", True):
                final_comment = f"[КРИТИЧНО / НЕ ОК] {final_comment}"

            # format the final dict to exactly match our sheet columns
            import datetime
            current_date = datetime.date.today().strftime("%Y-%m-%d")

            return {
                "Дата": current_date,
                "Тип звернення": ai_data.get("type_of_call", "Вхідний"),
                "Номер телефону": phone_number,
                "Філія": ai_data.get("branch", ""),
                "Менеджер": ai_data.get("manager_name", ""),
                "Початок розмови, представлення": ai_data.get("has_introduction", 0),
                "Чи дізнвся менеджер кузов атвомобіля": ai_data.get("asked_car_body", 0),
                "Чи дізнався менеджер рік автомобіля": ai_data.get("asked_car_year", 0),
                "Чи дізнався менеджр пробіг": ai_data.get("asked_mileage", 0),
                "Пропозиція про комплексну діагностику": ai_data.get("offered_complex_diagnostic", 0),
                "Дізнався які роботи робилися раніше": ai_data.get("asked_previous_works", 0),
                "Запис на сервіс, Дата": ai_data.get("booking_date", "Не записався"),
                "Завершення розмови прощання": ai_data.get("has_good_goodbye", 0),
                "Яка робота з топ 100 ": ai_data.get("work_type", "Слюсарні роботи"),
                "Чи дотримувався всіх інструкцій з топ 100 робіт Да/Ні": followed_all,
                "Яких рекоменадцій менеджер не дотримувався з топ 100 робіт": missed_str,
                "Результат": ai_data.get("result", ""),
                "Оцінка ": score,  # the score sum column
                "Запчастини": ai_data.get("parts_discussed", ""),
                "Коментар": final_comment
            }

        except json.JSONDecodeError as jde:
            raw_content = chat_completion.choices[0].message.content if 'chat_completion' in locals() else 'Немає відповіді'
            logging.error(f"Помилка парсингу JSON від Groq: {jde}. Сирий вивід: {raw_content}")
            return {}
        except Exception as e:
            logging.error(f"Помилка Groq аналітика: {e}")
            return {}
import os
import pandas as pd

class CSVManager:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def append_row(self, data: dict):
        """Додає новий рядок аналітики в кінець CSV файлу та забезпечує кодування UTF-8 з BOM для Excel"""
        # Створюємо DataFrame з одного нового рядка
        new_row_df = pd.DataFrame([data])
        
        # Перевіряємо, чи існує файл
        if os.path.exists(self.csv_path):
            # Дописуємо в кінець існуючого файлу без перезапису заголовків
            new_row_df.to_csv(self.csv_path, mode='a', header=False, index=False, encoding='utf-8-sig')
        else:
            # Якщо файлу немає, створюємо новий із заголовками
            new_row_df.to_csv(self.csv_path, mode='w', header=True, index=False, encoding='utf-8-sig')
            
        # Завжди перевіряємо, чи файл на диску починається з UTF-8 BOM (b'\xef\xbb\xbf')
        # Це гарантує, що Excel відкриє його коректно, навіть якщо користувач редагував його вручну
        if os.path.exists(self.csv_path) and os.path.getsize(self.csv_path) > 0:
            try:
                with open(self.csv_path, 'rb') as f:
                    content = f.read()
                if not content.startswith(b'\xef\xbb\xbf'):
                    with open(self.csv_path, 'wb') as f:
                        f.write(b'\xef\xbb\xbf' + content)
            except Exception as e:
                import logging
                logging.error(f"Не вдалося додати BOM-заголовок до CSV файлу: {e}")
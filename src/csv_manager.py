import os
import csv

class CSVManager:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        # Ensure file exists with BOM and header placeholder
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                pass

    def append_row(self, data: dict):
        """Append a row to CSV with UTF-8 BOM. Header is written only if file is empty."""
        file_exists = os.path.exists(self.csv_path) and os.path.getsize(self.csv_path) > 0
        with open(self.csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
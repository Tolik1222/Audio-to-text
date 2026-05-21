'''Google Drive & Sheets helper utilities.
Provides methods to download audio files from a source folder, upload files, create a sheet, copy a Google Sheet template, append rows, and apply red formatting.
'''
import os
import io
import logging
from typing import List, Dict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

class GoogleServicesManager:
    def __init__(self, credentials_path: str = "credentials.json"):
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Google credentials not found: {credentials_path}")
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        self.creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        self.drive = build('drive', 'v3', credentials=self.creds)
        self.sheets = build('sheets', 'v4', credentials=self.creds)
        logging.info('✅ Google services initialised')

    # ---------- Drive helpers ----------
    def list_audio_files(self, folder_id: str) -> List[Dict[str, str]]:
        """Return list of dicts {'id': ..., 'name': ...} for .mp3 files in folder_id."""
        query = f"'{folder_id}' in parents and mimeType='audio/mpeg' and trashed=false"
        result = self.drive.files().list(q=query, fields='files(id,name)').execute()
        return result.get('files', [])

    def download_file(self, file_id: str, dest_path: str) -> None:
        request = self.drive.files().get_media(fileId=file_id)
        fh = io.FileIO(dest_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        logging.info(f"📥 Downloaded {dest_path} (id={file_id})")

    def upload_file(self, local_path: str, folder_id: str) -> str:
        """Upload a local file to target Drive folder and return the new file ID."""
        file_name = os.path.basename(local_path)
        media = MediaFileUpload(local_path, resumable=True)
        body = {"name": file_name, "parents": [folder_id]}
        file = self.drive.files().create(body=body, media_body=media, fields='id').execute()
        logging.info(f"📤 Uploaded {file_name} to Drive (id={file.get('id')})")
        return file.get('id')

    def move_file(self, file_id: str, new_folder_id: str) -> None:
        """Move a file to a new folder in Google Drive."""
        # Retrieve the existing parents to remove
        file = self.drive.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents', []))
        
        # Move the file to the new folder
        self.drive.files().update(
            fileId=file_id,
            addParents=new_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        logging.info(f"🚚 Moved file {file_id} to folder {new_folder_id}")

    # ---------- Sheet helpers ----------
    def create_sheet(self, title: str, folder_id: str = None) -> str:
        """Create a new blank Google Sheet and return its ID."""
        body = {
            "name": title, 
            "mimeType": "application/vnd.google-apps.spreadsheet"
        }
        if folder_id:
            body["parents"] = [folder_id]
            
        sheet = self.drive.files().create(body=body, fields='id').execute()
        sheet_id = sheet.get('id')
        logging.info(f"📄 Created new sheet '{title}' with id {sheet_id}")
        return sheet_id

    def copy_sheet_template(self, template_id: str, new_name: str) -> str:
        """Copy an existing sheet template and return the new sheet ID."""
        body = {"name": new_name}
        copied = self.drive.files().copy(fileId=template_id, body=body).execute()
        new_id = copied['id']
        logging.info(f"📄 Created sheet copy '{new_name}' with id {new_id}")
        return new_id

    def find_sheet_by_name(self, name: str, folder_id: str = None) -> str:
        """Find a Google Sheet by its name, optionally in a specific folder."""
        query = f"name='{name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
            
        result = self.drive.files().list(q=query, fields='files(id,name)').execute()
        files = result.get('files', [])
        if files:
            logging.info(f"🔍 Found existing sheet '{name}' (id={files[0]['id']})")
            return files[0]['id']
        return None

    def setup_sheet_headers(self, sheet_id: str, headers: List[str]) -> None:
        """Set up headers for a new sheet and make them bold."""
        self.append_row(sheet_id, headers)
        
        # Make headers bold
        requests = [{
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True}
                    }
                },
                "fields": "userEnteredFormat(textFormat)"
            }
        }]
        self.sheets.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id, 
            body={"requests": requests}
        ).execute()
        logging.info(f"📝 Added headers to sheet {sheet_id}")

    def append_row(self, sheet_id: str, values: List[str]) -> str:
        """Append a row of values to the sheet and return the updated range."""
        body = {"values": [values]}
        result = (
            self.sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=sheet_id,
                range='A1',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body,
            )
            .execute()
        )
        updated_range = result.get('updates', {}).get('updatedRange')
        logging.info(f"🧩 Appended row to sheet {sheet_id} (range {updated_range})")
        return updated_range

    def apply_red_formatting(self, sheet_id: str, row_index: int, col_index: int) -> None:
        """Apply red background to a single cell (0‑based indices)."""
        requests = [{
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": row_index,
                    "endRowIndex": row_index + 1,
                    "startColumnIndex": col_index,
                    "endColumnIndex": col_index + 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 1, "green": 0, "blue": 0},
                        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}}
                    }},
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        }]
        self.sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()
        logging.info(f"🔴 Applied red formatting to sheet {sheet_id} cell ({row_index+1}, {col_index+1})")

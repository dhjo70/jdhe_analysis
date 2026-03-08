"""
Google Drive API 통합 모듈입니다.
OAuth 2.0 흐름(credentials.json -> token.json)을 통해 인증을 처리하며,
특정 드라이브 폴더의 하위 폴더(Volume, Issue) 구조 스캔 및 PDF 파일 다운로드를 담당합니다.
"""

import os
import io
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    """
    Drive v3 API 서비스 객체를 초기화하고 반환합니다.
    기존에 발급받은 token.json이 있다면 재사용하고, 만료되었거나 없다면
    credentials.json을 이용해 로컬 서버 인증(OAuth) 절차를 거칩니다.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("credentials.json  ϴ. Ǿ° Ȯ .")
                
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def get_subfolders(service, parent_id):
    """
    지정된 부모 폴더 ID를 기준으로, 쓰레기통에 가지 않은 활성 하위 '폴더'들의 목록을 반환합니다.
    (반환 리스트 내 객체 형태: {"id": "폴더고유ID", "name": "폴더이름"})
    페이지네이션(NextPageToken)을 자동으로 처리하여 100개가 넘어가는 폴더 구조도 모두 불러옵니다.
    """
    items = []
    page_token = None
    while True:
        try:
            results = service.files().list(
                q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                pageSize=100,
                fields="nextPageToken, files(id, name)",
                orderBy="name",
                pageToken=page_token
            ).execute()
            
            items.extend(results.get('files', []))
            page_token = results.get('nextPageToken', None)
            if not page_token:
                break
        except Exception as e:
            print(f"폴더 목록 조회 중 오류 발생: {e}")
            break
            
    return items

def get_pdfs_in_folder(service, folder_id):
    """
    지정된 폴더 내부에 존재하는 마임타입(MIME Type)이 'application/pdf'인 파일들의 목록만 반환합니다.
    """
    items = []
    page_token = None
    while True:
        try:
            # application/pdf 마임타입만 필터링
            results = service.files().list(
                q=f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false",
                pageSize=100,
                fields="nextPageToken, files(id, name)",
                orderBy="name",
                pageToken=page_token
            ).execute()
            
            items.extend(results.get('files', []))
            page_token = results.get('nextPageToken', None)
            if not page_token:
                break
        except Exception as e:
            print(f"PDF 목록 조회 중 오류 발생: {e}")
            break
            
    return items

def download_file(service, file_id, save_path):
    """
    단일 파일의 ID를 전달받아, MediaIoBaseDownload를 통해 바이너리 형태로 지정된 경로(save_path)에 로컬 저장합니다.
    다운로드가 성공적으로 완료되면 True를, 실패하면 False를 반환합니다.
    """
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            # print(f"Download {int(status.progress() * 100)}%.")
            
        fh.seek(0)
        with open(save_path, 'wb') as f:
            f.write(fh.read())
        return True
    except Exception as e:
        print(f"파일 다운로드 실패 ({file_id}): {e}")
        return False

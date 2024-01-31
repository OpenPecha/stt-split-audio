import psycopg2
import os
from dotenv import load_dotenv

def get_time_span(filename):

    filename = filename.replace(".wav", "")
    filename = filename.replace(".WAV", "")
    filename = filename.replace(".mp3", "")
    filename = filename.replace(".MP3", "")
    try:
        if "_to_" in filename:
            start, end = filename.split("_to_")
            start = start.split("_")[-1]
            end = end.split("_")[0]
            end = float(end)
            start = float(start)
            return (end - start)/1000
        else:
            start, end = filename.split("-")
            start = start.split("_")[-1]
            end = end.split("_")[0]
            end = float(end)
            start = float(start)
            return abs(end - start)
    except Exception as err:
        print(f"filename is:'{filename}'. Could not parse to get time span.")
        return 0

def get_max_db_id():

    from dotenv import load_dotenv
    
    try:
        load_dotenv(dotenv_path='../util/.env')
    except Exception as e:
        print(f"Check the .env file in util: {str(e)}")

    HOST = os.environ.get('HOST')
    DBNAME = os.environ.get('DBNAME')
    DBUSER = os.environ.get('DBUSER')
    PASSWORD = os.environ.get('PASSWORD')
    # SQL query to find the maximum ID
    query = """select max(id) from "Task" t"""

    try:
        # Connect to your postgres DB
        conn = psycopg2.connect(host=HOST, dbname=DBNAME, user=DBUSER, password=PASSWORD)

        # Open a cursor to perform database operations
        cur = conn.cursor()

        # Execute the query
        cur.execute(query)

        # Fetch and print the result
        max_id = cur.fetchone()[0]
        print(f"The maximum ID in the 'Task' table is: {max_id}")

        # Close the cursor and the connection
        cur.close()
        conn.close()
        return max_id

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
def read_spreadsheet(sheet_id):
    import pandas as pd
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    df = pd.read_csv(url)
    return df

def collect_segments(prefix, source, destination_folder):
    from pathlib import Path
    import shutil
    # Source folder as a Path object
    source = Path(source)

    # Use a list comprehension to find all folders with names starting with the specified prefix
    source_folders = [folder for folder in source.iterdir() if folder.is_dir() and folder.name.startswith(prefix)]

    # Destination folder as a Path object
    destination_folder = Path(destination_folder)

    # Create the destination folder if it doesn't exist
    destination_folder.mkdir(parents=True, exist_ok=True)

    # Iterate through the source folders
    for source_folder in source_folders:
        # Iterate through the contents of each source folder
        for wav_file in source_folder.glob('**/*.wav'):
            # Create a destination path by joining the destination folder with the filename
            destination_path = destination_folder / wav_file.name
            
            # Copy the .wav file to the destination folder
            shutil.copy2(wav_file, destination_path)
            print(f"Copied {wav_file} to {destination_path}")

    print("Copying complete.")



import io
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def create_drive_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('../util/token.json'):
        creds = Credentials.from_authorized_user_file('../util/token.json')
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '../util/credentials.json', ['https://www.googleapis.com/auth/drive'])
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('../util/token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

# Create the drive service
drive_service = create_drive_service()

def download_audio_gdrive(gd_url, file_name):

    from pathlib import Path

    Path('full_audio').mkdir(parents=True, exist_ok=True)
    
    if Path('full_audio', file_name).exists():
        print(f"File {file_name} already exists.")
        return
    
    file_id = gd_url.split("/")[-2] if "drive.google.com" in gd_url else gd_url
    # Download the file
    request = drive_service.files().get_media(fileId=file_id)

    # Download the file
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")

    # Save the file locally
    with open(f'full_audio/{file_name}', 'wb') as f:
        f.write(fh.getbuffer())
        print("File downloaded successfully.")
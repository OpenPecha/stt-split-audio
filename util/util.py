import os
import psycopg2
import shutil
from dotenv import load_dotenv
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import pandas as pd
from pyannote.audio import Pipeline
from pydub import AudioSegment
import librosa
import torchaudio
from tqdm.notebook import tqdm
import re

def get_time_span(filename):
    """
    Extracts the time span in seconds from a filename.
    
    Args:
        filename (str): The filename from which to extract the time span.
    
    Returns:
        float: The time span in seconds, or 0 if extraction fails.
    """
    filename = filename.lower().replace(".wav", "").replace(".mp3", "")
    try:
        if "_to_" in filename:
            start, end = filename.split("_to_")
        else:
            start, end = filename.split("-")
        start = float(start.split("_")[-1])
        end = float(end.split("_")[0])
        return (end - start) / 1000 if "_to_" in filename else abs(end - start)
    except Exception as err:
        print(f"Error parsing filename '{filename}': {err}")
        return 0

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.
    
    Returns:
        connection: A psycopg2 connection object.
    """
    try:
        load_dotenv(dotenv_path="../util/.env")
    except Exception as e:
        print(f"Check the .env file in util: {str(e)}")

    return psycopg2.connect(
        host=os.environ.get("HOST"),
        dbname=os.environ.get("DBNAME"),
        user=os.environ.get("DBUSER"),
        password=os.environ.get("PASSWORD")
    )

def get_all_url():
    """
    Fetches all URLs from the 'Task' table in the database.
    
    Returns:
        list: A list of URLs, or None if an error occurs.
    """
    query = """SELECT url FROM "Task" t"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        all_urls = [url[0] for url in cur.fetchall()]
        cur.close()
        conn.close()
        print(f"Fetched all URLs from 'Task' table.")
        return all_urls
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_all_file_name():
    """
    Fetches all file names from the 'Task' table in the database.
    
    Returns:
        list: A list of file names, or None if an error occurs.
    """
    query = """SELECT file_name FROM "Task" t"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        all_filenames = [filename[0] for filename in cur.fetchall()]
        cur.close()
        conn.close()
        print(f"Fetched all file names from 'Task' table.")
        return all_filenames
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_max_db_id():
    """
    Fetches the maximum ID from the 'Task' table in the database.
    
    Returns:
        int: The maximum ID, or None if an error occurs.
    """
    query = """SELECT MAX(id) FROM "Task" t"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        max_id = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"Maximum ID in 'Task' table: {max_id}")
        return max_id
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def read_spreadsheet(sheet_id):
    """
    Reads a Google Spreadsheet as a Pandas DataFrame.
    
    Args:
        sheet_id (str): The ID of the Google Spreadsheet.
    
    Returns:
        DataFrame: A Pandas DataFrame containing the spreadsheet data.
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    df = pd.read_csv(url)
    return df


def collect_segments(prefix, source, destination_folder):
    """
    Collects audio segments from source folders starting with a given prefix
    and copies them to the destination folder.
    
    Args:
        prefix (str): The prefix to filter source folders.
        source (str): The path to the source folder.
        destination_folder (str): The path to the destination folder.
    """
    source = Path(source)
    destination_folder = Path(destination_folder)
    destination_folder.mkdir(parents=True, exist_ok=True)

    for source_folder in source.iterdir():
        if source_folder.is_dir() and source_folder.name.startswith(prefix):
            for wav_file in source_folder.glob("**/*.wav"):
                destination_path = destination_folder / wav_file.name
                shutil.copy2(wav_file, destination_path)
                print(f"Copied {wav_file} to {destination_path}")

    print("Copying complete.")

def create_drive_service():
    """
    Creates a Google Drive service object for interacting with the Google Drive API.
    
    Returns:
        Resource: A Google Drive API service resource.
    """
    creds = None
    if os.path.exists("../util/token.json"):
        creds = Credentials.from_authorized_user_file("../util/token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "../util/credentials.json", ["https://www.googleapis.com/auth/drive"]
            )
            creds = flow.run_local_server(port=0)
        with open("../util/token.json", "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


# Create the drive service
drive_service = create_drive_service()

def download_audio_gdrive(gd_url, file_name):
    """
    Downloads an audio file from Google Drive to a local directory.
    
    Args:
        gd_url (str): The Google Drive URL or file ID.
        file_name (str): The desired name of the downloaded file.
    """
    Path("full_audio").mkdir(parents=True, exist_ok=True)

    if Path("full_audio", file_name).exists():
        print(f"File {file_name} already exists.")
        return

    file_id = gd_url.split("/")[-2] if "drive.google.com" in gd_url else gd_url
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")

    with open(f"full_audio/{file_name}", "wb") as f:
        f.write(fh.getbuffer())
        print(f"File {file_name} downloaded successfully.")



upper_limit = 10
lower_limit = 2


def sec_to_millis(sec):
    return sec * 1000


def frame_to_sec(frame, sr):
    return frame / sr


def sec_to_frame(sec, sr):
    return sec * sr


HYPER_PARAMETERS = {
    # onset/offset activation thresholds
    "onset": 0.5,
    "offset": 0.5,
    # remove speech regions shorter than that many seconds.
    "min_duration_on": 2.0,
    # fill non-speech regions shorter than that many seconds.
    "min_duration_off": 0.0,
}

pipeline = Pipeline.from_pretrained(
    "pyannote/voice-activity-detection",
    use_auth_token="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",
)
pipeline.instantiate(HYPER_PARAMETERS)


def save_segment(segment, folder, prefix, id, start_ms, end_ms):
    os.makedirs(f"after_split/{folder}", exist_ok=True)
    segment.export(
        f"after_split/{folder}/{prefix}_{id:04}_{int(start_ms)}_to_{int(end_ms)}.wav",
        format="wav",
        parameters=["-ac", "1", "-ar", "16000"],
    )


def delete_file(file):
    os.remove(file)


def split_audio(audio_file, output_folder):
    """splits the full audio file into segments based on
    Voice Activity Detection
    librosa split based on volume and
    blind chop to fit the range of upper_limit to lower_limit

    Args:
        audio_file (str): path to full audio file
        output_folder (str): where to store the split segments
    """
    print(f"{audio_file} {output_folder}")
    vad = pipeline(audio_file)
    original_audio_segment = AudioSegment.from_file(audio_file)
    original_audio_ndarray, sampling_rate = torchaudio.load(audio_file)
    original_audio_ndarray = original_audio_ndarray[0]
    counter = 1
    for vad_span in vad.get_timeline().support():
        vad_segment = original_audio_segment[
            sec_to_millis(vad_span.start) : sec_to_millis(vad_span.end)
        ]
        vad_span_length = vad_span.end - vad_span.start
        if vad_span_length >= lower_limit and vad_span_length <= upper_limit:
            save_segment(
                segment=vad_segment,
                folder=output_folder,
                prefix=output_folder,
                id=counter,
                start_ms=sec_to_millis(vad_span.start),
                end_ms=sec_to_millis(vad_span.end),
            )
            print(
                f"{counter} {vad_span_length:.2f} {sec_to_millis(vad_span.start):.2f} {sec_to_millis(vad_span.end):.2f} vad"
            )
            counter += 1
        elif vad_span_length > upper_limit:
            non_mute_segment_splits = librosa.effects.split(
                original_audio_ndarray[
                    int(sec_to_frame(vad_span.start, sampling_rate)) : int(
                        sec_to_frame(vad_span.end, sampling_rate)
                    )
                ],
                top_db=30,
            )
            # print(non_mute_segment_splits)
            for split_start, split_end in non_mute_segment_splits:
                # print(f'non mute {(frame_to_sec(split_end, sampling_rate) - frame_to_sec(split_start, sampling_rate)):.2f} {vad_span.start + frame_to_sec(split_start, sampling_rate):.2f} {vad_span.start + frame_to_sec(split_end, sampling_rate):.2f} {split_start} {split_end}')
                segment_split = original_audio_segment[
                    sec_to_millis(
                        vad_span.start + frame_to_sec(split_start, sampling_rate)
                    ) : sec_to_millis(
                        vad_span.start + frame_to_sec(split_end, sampling_rate)
                    )
                ]
                segment_split_duration = (
                    vad_span.start + frame_to_sec(split_end, sampling_rate)
                ) - (vad_span.start + frame_to_sec(split_start, sampling_rate))
                if (
                    segment_split_duration >= lower_limit
                    and segment_split_duration <= upper_limit
                ):
                    save_segment(
                        segment=segment_split,
                        folder=output_folder,
                        prefix=output_folder,
                        id=counter,
                        start_ms=sec_to_millis(
                            vad_span.start + frame_to_sec(split_start, sampling_rate)
                        ),
                        end_ms=sec_to_millis(
                            vad_span.start + frame_to_sec(split_end, sampling_rate)
                        ),
                    )
                    print(
                        f"{counter} {segment_split_duration:.2f} {sec_to_millis(vad_span.start + frame_to_sec(split_start, sampling_rate)):.2f} {sec_to_millis(vad_span.start + frame_to_sec(split_end, sampling_rate)):.2f} split"
                    )
                    counter += 1
                elif segment_split_duration > upper_limit:
                    chop_length = segment_split_duration / 2
                    while chop_length > upper_limit:
                        chop_length = chop_length / 2
                    for j in range(int(segment_split_duration / chop_length)):
                        segment_split_chop = original_audio_segment[
                            sec_to_millis(
                                vad_span.start
                                + frame_to_sec(split_start, sampling_rate)
                                + chop_length * j
                            ) : sec_to_millis(
                                vad_span.start
                                + frame_to_sec(split_start, sampling_rate)
                                + chop_length * (j + 1)
                            )
                        ]
                        save_segment(
                            segment=segment_split_chop,
                            folder=output_folder,
                            prefix=output_folder,
                            id=counter,
                            start_ms=sec_to_millis(
                                vad_span.start
                                + frame_to_sec(split_start, sampling_rate)
                                + chop_length * j
                            ),
                            end_ms=sec_to_millis(
                                vad_span.start
                                + frame_to_sec(split_start, sampling_rate)
                                + chop_length * (j + 1)
                            ),
                        )
                        print(
                            f"{counter} {chop_length:.2f} {sec_to_millis(vad_span.start + frame_to_sec(split_start, sampling_rate) + chop_length * j ):.2f} {sec_to_millis(vad_span.start + frame_to_sec(split_start, sampling_rate) + chop_length * ( j + 1 )):.2f} chop"
                        )
                        counter += 1


def split_audio_files(prefix, ext):
    """
    Process and split all audio files with a specific prefix and extension.

    Args:
        prefix (str): Prefix for the filenames.
        ext (str): File extension of the audio files.
    """
    stt_files = [
        filename
        for filename in os.listdir("full_audio")
        if filename.startswith(prefix)
        and os.path.isfile(os.path.join("full_audio", filename))
    ]
    # print(stt_files)
    for stt_file in tqdm(stt_files):
        # print(stt_file)
        stt_file = stt_file.split(".")[0]
        split_audio(audio_file=f"./full_audio/{stt_file}.{ext}", output_folder=stt_file)
        # delete_file(file=f"./{stt_folder}/{stt_folder}.wav")



def clean_transcription(text):
    """
    Cleans and normalizes Tibetan transcription text to make it syntactically correct.

    Args:
        text (str): The input transcription text.

    Returns:
        str: The cleaned and normalized transcription text.
    """
    # Replace newline and tab characters with spaces
    text = text.replace('\n', ' ')
    text = text.replace('\t', ' ')
    text = text.strip()
    
    # Normalize specific Tibetan punctuation and characters
    text = re.sub("༌", "་", text)  # Normalize tsak
    text = re.sub("༎", "།", text)  # Normalize double shae
    text = re.sub("༔", "།", text)
    text = re.sub("༏", "།", text)
    text = re.sub("༐", "།", text)
    text = re.sub("ཽ", "ོ", text)  # Normalize
    text = re.sub("ཻ", "ེ", text)  # Normalize

    # Collapse multiple spaces and Tibetan spaces
    text = re.sub(r"\s+།", "།", text)
    text = re.sub(r"།+", "།", text)
    text = re.sub(r"།", "། ", text)
    text = re.sub(r"\s+་", "་", text)
    text = re.sub(r"་+", "་", text)
    text = re.sub(r"\s+", " ", text)

    # Normalize repetitive sequences of Tibetan characters
    text = re.sub(r"ཧཧཧ+", "ཧཧཧ", text)
    text = re.sub(r'ཧི་ཧི་(ཧི་)+', r'ཧི་ཧི་ཧི་', text)
    text = re.sub(r'ཧེ་ཧེ་(ཧེ་)+', r'ཧེ་ཧེ་ཧེ་', text)
    text = re.sub(r'ཧ་ཧ་(ཧ་)+', r'ཧ་ཧ་ཧ་', text)
    text = re.sub(r'ཧོ་ཧོ་(ཧོ་)+', r'ཧོ་ཧོ་ཧོ་', text)
    text = re.sub(r'ཨོ་ཨོ་(ཨོ་)+', r'ཨོ་ཨོ་ཨོ་', text)

    # Remove specific punctuation marks and special characters
    chars_to_ignore_regex = "[\,\?\.\!\-\;\:\"\“\%\‘\”\�\/\{\}\(\)༽》༼《༄༅༈༑༠'|·×༆༸༾ཿ྄྅྆྇ྋ࿒ᨵ​’„╗᩺╚༿᫥ྂ༊ྈ༁༂༃༇༈༉༒༷༺༻࿐࿑࿓࿔࿙࿚༴࿊]"
    text = re.sub(chars_to_ignore_regex, '', text) + " "
    
    return text

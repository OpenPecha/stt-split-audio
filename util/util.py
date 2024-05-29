import psycopg2
import os
from dotenv import load_dotenv
from tqdm.notebook import tqdm


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
            return (end - start) / 1000
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


def get_all_url():

    from dotenv import load_dotenv

    try:
        load_dotenv(dotenv_path="../util/.env")
    except Exception as e:
        print(f"Check the .env file in util: {str(e)}")

    HOST = os.environ.get("HOST")
    DBNAME = os.environ.get("DBNAME")
    DBUSER = os.environ.get("DBUSER")
    PASSWORD = os.environ.get("PASSWORD")
    # SQL query to find the maximum ID
    query = """select url from "Task" t"""

    try:
        # Connect to your postgres DB
        conn = psycopg2.connect(
            host=HOST, dbname=DBNAME, user=DBUSER, password=PASSWORD
        )

        # Open a cursor to perform database operations
        cur = conn.cursor()

        # Execute the query
        cur.execute(query)

        # Fetch and print the result
        all_urls = cur.fetchall()
        print(f"All the url in the 'Task' table is fetched")

        # Close the cursor and the connection
        cur.close()
        conn.close()
        all_urls = list(map(lambda x: x[0], all_urls))
        return all_urls

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_all_file_name():

    try:
        load_dotenv(dotenv_path="../util/.env")
    except Exception as e:
        print(f"Check the .env file in util: {str(e)}")

    HOST = os.environ.get("HOST")
    DBNAME = os.environ.get("DBNAME")
    DBUSER = os.environ.get("DBUSER")
    PASSWORD = os.environ.get("PASSWORD")
    # SQL query to find the maximum ID
    query = """select file_name from "Task" t"""

    try:
        # Connect to your postgres DB
        conn = psycopg2.connect(
            host=HOST, dbname=DBNAME, user=DBUSER, password=PASSWORD
        )

        # Open a cursor to perform database operations
        cur = conn.cursor()

        # Execute the query
        cur.execute(query)

        # Fetch and print the result
        all_urls = cur.fetchall()
        print(f"All the file_name in the 'Task' table is fetched")

        # Close the cursor and the connection
        cur.close()
        conn.close()
        all_urls = list(map(lambda x: x[0], all_urls))
        return all_urls

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_max_db_id():

    from dotenv import load_dotenv

    try:
        load_dotenv(dotenv_path="../util/.env")
    except Exception as e:
        print(f"Check the .env file in util: {str(e)}")

    HOST = os.environ.get("HOST")
    DBNAME = os.environ.get("DBNAME")
    DBUSER = os.environ.get("DBUSER")
    PASSWORD = os.environ.get("PASSWORD")
    # SQL query to find the maximum ID
    query = """select max(id) from "Task" t"""

    try:
        # Connect to your postgres DB
        conn = psycopg2.connect(
            host=HOST, dbname=DBNAME, user=DBUSER, password=PASSWORD
        )

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
    source_folders = [
        folder
        for folder in source.iterdir()
        if folder.is_dir() and folder.name.startswith(prefix)
    ]

    # Destination folder as a Path object
    destination_folder = Path(destination_folder)

    # Create the destination folder if it doesn't exist
    destination_folder.mkdir(parents=True, exist_ok=True)

    # Iterate through the source folders
    for source_folder in source_folders:
        # Iterate through the contents of each source folder
        for wav_file in source_folder.glob("**/*.wav"):
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
    if os.path.exists("../util/token.json"):
        creds = Credentials.from_authorized_user_file("../util/token.json")
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "../util/credentials.json", ["https://www.googleapis.com/auth/drive"]
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("../util/token.json", "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


# Create the drive service
drive_service = create_drive_service()


def download_audio_gdrive(gd_url, file_name):

    from pathlib import Path

    Path("full_audio").mkdir(parents=True, exist_ok=True)

    if Path("full_audio", file_name).exists():
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
    with open(f"full_audio/{file_name}", "wb") as f:
        f.write(fh.getbuffer())
        print("File downloaded successfully.")


from pyannote.audio import Pipeline
from pydub import AudioSegment
import librosa
import torchaudio
import os

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

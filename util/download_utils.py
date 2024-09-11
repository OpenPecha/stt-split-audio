import subprocess
import requests

def download_s3_file(s3_path, local_filename):
    """
    Downloads a file from S3 using AWS CLI.

    Args:
    - s3_path (str): S3 path of the file to download.
    - local_filename (str): Local filename to save the downloaded file.

    Returns:
    - bool: True if download successful, False otherwise.
    """
    try:
        s3_bucket = "monlam.ai.stt"  # Replace with your S3 bucket name

        # Run aws s3 cp command to download the file
        download_command = f"aws s3 cp s3://{s3_bucket}/{s3_path} {local_filename}"
        subprocess.run(download_command, shell=True, check=True)
        print(f"Downloaded {s3_path} to {local_filename}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {s3_path}: {e}")
        return False
    

def download_url_file(url, local_filename):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(local_filename.strip(), 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded {local_filename.strip()}")
    else:
        print(f"Failed to download {local_filename.strip()} from {url}. Status code: {response.status_code}")



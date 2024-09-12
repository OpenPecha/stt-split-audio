import os
import sys
import subprocess

sys.path.append('../util')

from google_utils import read_spreadsheet
from db_utils import get_max_db_id
from tqdm.auto import tqdm
import pandas as pd
from pathlib import Path
from common_utils import parse_args_and_load_config
from docx_utils import transfer_text


def main(config):
    # Read configuration from the loaded JSON
    dept = config['DEPARTMENT']
    from_id = config['FROM_ID']
    to_id = config['TO_ID']
    id_col = config['ID_COL']
    sr_col = config['SR_COL']
    segment_dir = config['SEGMENT_DIR']
    sheet_id = config['SHEET_ID']
    group_id = config['GROUP_ID']

    # Read the spreadsheet
    df = read_spreadsheet(sheet_id=sheet_id)

    # Read the CSV file with existing file names
    existing_files_df = pd.read_csv(f'{dept}.csv')  # Replace with your actual CSV file name

    # List to store matching rows
    matching_rows = []

    for index, row in df.iterrows():
        id = row[id_col]
        sr_no = row[sr_col]

        if sr_no >= from_id and sr_no <= to_id:
            print(id, sr_no)
            matching_rows.extend(existing_files_df[existing_files_df['file_name'].str.startswith(f"{id}_")].to_dict('records'))

    # Convert the matching rows to a DataFrame
    matching_rows_df = pd.DataFrame(matching_rows)
    # Drop any "Unnamed" columns from the DataFrame
    matching_rows_df = matching_rows_df.loc[:, ~matching_rows_df.columns.str.contains('^Unnamed')]
    # Save the matching rows to 'pc.csv' without including the index
    matching_rows_df.head()
    # Save the matching rows  without including the index
    matching_rows_df.to_csv(f"{dept}_{from_id}_to_{to_id}.tsv", index=False, sep="\t")

    temp = []

    for index, row in df.iterrows():
        id = row[id_col]
        sr_no = row[sr_col]

        if sr_no >= from_id and sr_no <= to_id:
            print(id, sr_no)
            transfer_text_df, status = transfer_text(f'etexts/{id}.txt', f"{dept}_{from_id}_to_{to_id}.tsv", id)
            temp.append(transfer_text_df)
            print(status)

    transfered_text_df = pd.concat(temp)  
    transfered_text_df.head()

    transfered_text_df.fillna('', inplace=True)
    transfered_text_df = transfered_text_df[transfered_text_df['inference_transcript'].apply(lambda x: len(x) < 500)]
    transfered_text_df = transfered_text_df.sort_values('file_name')
    transfered_text_df = transfered_text_df.reset_index(drop=True)

    group_id = group_id
    last_db_id = get_max_db_id()

    transfered_text_df['group_id'] = group_id
    transfered_text_df['state'] = 'transcribing'
    transfered_text_df['id'] = matching_rows_df.index + last_db_id + 1

    transfered_text_df.to_csv(f"{dept}_{group_id}_{from_id}_to_{to_id}.csv", index=False)
    
    
if __name__ == "__main__":
    # Parse arguments and load config
    config = parse_args_and_load_config()

    # Run the main pipeline logic
    main(config)

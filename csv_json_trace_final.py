import os
import csv
import json
from pathlib import Path
from datetime import datetime
import re

def csv_to_json(csv_file_path, json_file_path):
    data = []

    # Read CSV file and convert to a list of dictionaries
    with open(csv_file_path, 'r') as CSV_file:
        csv_reader = csv.DictReader(CSV_file)
        data = list(csv_reader)

    # Write JSON file
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)

def extract_timestamp(entry):
    match = re.search(r'\d{2}:\d{2}:\d{2}\.\d+', entry["_raw"])
    return match.group() if match else ""

def extract_log_type(entry):
    match = re.search(r'\/([a-zA-Z_]+)\d*\.debug', entry["source"])
    return match.group(1) if match else ""

def extract_message_type(entry):
    match = re.search(r'\b(?:m|MTI)(\d{4})\b', entry["_raw"])
    return match.group(1) if match else ""

message_descriptions = {
    "0100": "Authorization Request By Acquirer",
    # ... (add other message types and descriptions as needed)
}

def main():
    # Check if CSV file exists in Downloads folder
    downloads_csv_path = Path.home() / 'Downloads' / 'input.csv'
    if downloads_csv_path.exists():
        csv_file_path = downloads_csv_path
    else:
        # Prompt user for CSV file path
        csv_file_path = get_csv_path_from_user()

    # Convert CSV to JSON
    json_file_path = os.path.join(os.path.dirname(csv_file_path), 'output.json')
    csv_to_json(csv_file_path, json_file_path)

    # Read data from the output.json file
    with open('output.json', 'r') as file:
        data = json.load(file)

    # Sort data based on the timestamp in the "raw" field excluding the first field
    data_sorted = sorted(data, key=lambda x: extract_timestamp(x))

    # Initialize variables for start and end times
    log_type_times = {}

    # Create rows for the HTML table with additional "Time," "Log Type," and "Message Type" columns
    table_rows = []
    for entry in data_sorted:
        timestamp = entry["_time"]
        host = entry["host"]
        source = entry["source"]
        raw_data = entry["_raw"].split(' ', 1)[1]  # Extract without the first field
        extracted_time = extract_timestamp(entry)
        log_type = extract_log_type(entry)
        message_type = extract_message_type(entry)
        description = message_descriptions.get(message_type, "")

        # Check if the log type is pos_apifmt
        if log_type not in log_type_times:
            log_type_times[log_type] = {"start_time": None, "end_time": None}

        # Check for "Sent" or "Received" in the raw data
        if "Sent" in raw_data and log_type_times[log_type]["start_time"] is None:
            log_type_times[log_type]["start_time"] = extracted_time
        elif "Received" in raw_data:
            log_type_times[log_type]["end_time"] = extracted_time

        # Concatenate description to message type if available
        message_with_description = f"{message_type} - {description}" if description else message_type

        # Check if "r96" or "r08" is present in the "Raw Data" column
        row_style = "background-color: orange;" if any(code in raw_data for code in ["r96", "r08"]) else ""

        table_rows.append(
            f"<tr style='{row_style}'><td>{timestamp}</td><td>{host}</td><td>{source}</td>"
            f"<td>{extracted_time}</td><td>{raw_data.replace(extracted_time, '', 1)}</td>"
            f"<td>{log_type}</td><td>{message_with_description}</td></tr>"
        )

    # Create HTML table with start and end times for each log type
    html_table = f"""
    <html>
    <head>
        <style>
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            th, td {{
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }}
            th {{
                background-color: #f2f2f2;
                text-align: center; /* Center the text */
            }}
        </style>
    </head>
    <body>

    <h2 style="text-align:center;">Trace Table Information</h2>

    <table>
        <tr>
            <th>Splunk Timestamp</th>
            <th>Host</th>
            <th>Source</th>
            <th>Time in PDT</th>
            <th>Raw Data</th>
            <th>Log Type</th>
            <th>Message Type</th>
        </tr>
        """ + "".join(table_rows) + """
    </table>

    <!-- Add start and end times for each log type under the table -->
    """
    for log_type, times in log_type_times.items():
        html_table += f"<p>{log_type} Start Time: {times['start_time']}</p>\n"
        html_table += f"<p>{log_type} End Time: {times['end_time']}</p>\n"

    html_table += """
    </body>
    </html>
    """

    # Write HTML table to a file in the same location as the CSV file
    output_html_path = os.path.join(os.path.dirname(csv_file_path), 'output_table.html')
    with open(output_html_path, 'w') as html_file:
        html_file.write(html_table)

    print(f"HTML table is created and saved to {output_html_path}.")

def get_csv_path_from_user():
    # Get the user's home directory
    home_dir = Path.home()

    # Construct the full path of the download folder
    downloads_folder = home_dir / 'Downloads'

    # Specify the file name
    csv_file_name = input("Enter the CSV file name (including extension): ")

    # Construct the full path to the CSV file
    csv_file_path = downloads_folder / csv_file_name
    return csv_file_path

if __name__ == "__main__":
    main()

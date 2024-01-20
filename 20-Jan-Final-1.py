import json
import re
from pathlib import Path

# Function to extract timestamp without the first field
def extract_timestamp(entry):
    match = re.search(r'\d{2}:\d{2}:\d{2}\.\d+', entry["_raw"])
    return match.group() if match else ""

# Function to extract log type from the source field without numbers
def extract_log_type(entry):
    match = re.search(r'\/([a-zA-Z_]+)\d*\.debug', entry["source"])
    return match.group(1) if match else ""

# Function to extract message type from the raw data
def extract_message_type(entry):
    match = re.search(r'\b(?:m|MTI)(\d{4})\b', entry["_raw"])
    return match.group(1) if match else ""

# Dictionary mapping message types to descriptions
message_descriptions = {
    "0100": "Authorization Request By Acquirer",
    "0110": "Authorization Response By Acquirer",
    "1100": "Authorization Request By Acquirer",
    "0120": "Authorization Advice By Acquirer",
    "0121": "Authorization Advice Repeat By Issuer",
    "0130": "Authorization Advice Response By Acquirer",
    "0200": "Acquirer Financial Request",
    "0210": "Financial Response By Acquirer",
    "0220": "Acquirer Financial Advice",
    "0221": "Acquirer Financial Advice Repeat",
    "0230": "Issuer Response to Financial Advice By Acquirer",
    "0320": "Batch Upload By Acquirer",
    "0330": "Batch Upload Response By Acquirer",
    "0400": "Acquirer Reversal Request",
    "0410": "Acquirer Reversal Response",
    "0420": "Acquirer Reversal Advice",
    "0430": "Acquirer Reversal Advice Response",
    "0510": "Batch Settlement Response By Acquirer",
    "0800": "Network Management Request",
    "0810": "Network Management Response",
    "0820": "Network Management Advice",
}

# Specify the path of the previous script's output file
previous_output_file_path = 'output.json'

# Read data from the output.json file
with open(previous_output_file_path, 'r') as file:
    data = json.load(file)

# Sort data based on the timestamp in the "raw" field excluding the first field
data_sorted = sorted(data, key=lambda x: extract_timestamp(x))

# Initialize variables for start and end times
log_type_times = {}

# Create rows for the HTML table with additional "Time," "Log Type," and "Message Type" columns
table_rows = []
trace_numbers = set()
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

# Determine the location of the input CSV file
csv_file_path = Path(previous_output_file_path).parent / 'input.csv'

# Specify the output JSON file path in the same location as the input CSV file
output_json_file_path = csv_file_path.with_name('output.json')

# Specify the output HTML file path in the same location as the input CSV file
output_html_file_path = csv_file_path.with_name('output_table.html')

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

<!-- Add start and end times for each log type under the table header -->
"""
for log_type, times in log_type_times.items():
    html_table += f"<p>{log_type} Start Time: {times['start_time']}</p>\n"
    html_table += f"<p>{log_type} End Time: {times['end_time']}</p>\n"

# Continue with the rest of the HTML table
html_table += """
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

</body>
</html>
"""

# Write HTML table to a file in the same location as the input CSV file
with open(output_html_file_path, 'w') as html_file:
    html_file.write(html_table)

# Write output JSON to a file in the same location as the input CSV file
with open(output_json_file_path, 'w') as json_file:
    json.dump(data_sorted, json_file, indent=2)

print(f"Input CSV file path: {csv_file_path}")
print(f"Output JSON file is created and saved to {output_json_file_path}")
print(f"HTML table is created and saved to {output_html_file_path}")

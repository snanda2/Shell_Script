import json
from datetime import datetime
import re
import string

json_file_path = 'output.json'

# Function to recursively remove leading and trailing whitespaces, consecutive spaces, and consecutive tabs in a JSON object
def clean_json(obj):
    if isinstance(obj, dict):
        return {key.strip(): clean_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [clean_json(element) for element in obj]
    elif isinstance(obj, str):
        # Replace consecutive whitespace characters (spaces and tabs) with a single space
        cleaned_value = ' '.join(obj.split())

        # Remove all non-printable characters
        cleaned_value = ''.join(char for char in cleaned_value if char in string.printable)

        return cleaned_value
    else:
        return obj

# Define a function to extract timestamp without the first field
def extract_timestamp(entry):
    match = re.search(r'\d{2}:\d{2}:\d{2}\.\d+', entry["_raw"])
    return match.group() if match else ""

try:
    with open(json_file_path, 'r', encoding='utf-8') as file:
        json_content = file.read()
        cleaned_json_content = json.loads(json_content, object_hook=clean_json)
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")
    problematic_part = json_content[e.pos:e.pos + 10]  # Print the problematic part of the JSON
    print(f"Problematic part of JSON: {problematic_part}")
    exit(1)

# Sort data based on the timestamp in the "raw" field excluding the first field
sorted_json_content = sorted(cleaned_json_content, key=lambda x: extract_timestamp(x))

table_rows = []
# Rest of your code using the 'sorted_json_content' variable
for entry in sorted_json_content:
    # Your processing logic here
    
    host = entry["host"]
    source = entry["source"]
    msg_type = entry["msg_type"]
    proc_code = entry["proc_code"]
    resp_code = entry["resp_code"]
    trace_no = entry["trace_no"]
    raw_data = entry["_raw"].split(' ', 1)[1]  # Extract without the first field

    table_rows.append(
        f"<tr><td>{host}</td><td>{source}</td>"
        f"<td>{msg_type}</td><td>{proc_code}</td><td>{resp_code}</td><td>{trace_no}</td><td>{raw_data}</td></tr>"
        )

# Create HTML table
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
            text-align: center;
        }}
    </style>
</head>
<body>

<h2>Trace Table Information</h2>
<table>
    <tr>
        <th>Host</th>
        <th>Source</th>
        <th>Message Type</th>
        <th>Proc Code</th>
        <th>Resp Code</th>
        <th>Trace No</th>
        <th>Raw Data</th>
    </tr>
    {"".join(table_rows)}
</table>

</body>
</html>
"""

# Write HTML table to a file
with open('output_table.html', 'w') as html_file:
    html_file.write(html_table)

print("HTML table created and saved to output_table.html.")

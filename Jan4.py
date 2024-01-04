import json
from datetime import datetime
import re

# Read data from the output.json file
with open('output.json', 'r') as file:
    data = json.load(file)

# Define a function to extract timestamp without the first field
def extract_timestamp(entry):
    match = re.search(r'\d{2}:\d{2}:\d{2}\.\d+', entry["_raw"])
    return match.group() if match else ""

# Sort data based on the timestamp in the "raw" field excluding the first field
data_sorted = sorted(data, key=lambda x: extract_timestamp(x))

# Create rows for the HTML table with an additional "Time" column
table_rows = []
trace_numbers = set()
for entry in data_sorted:
    timestamp = entry["_time"]
    host = entry["host"]
    source = entry["source"]
    msg_type = entry["msg_type"]
    proc_code = entry["proc_code"]
    resp_code = entry["resp_code"]
    trace_no = entry["trace_no"]
    raw_data = entry["_raw"].split(' ', 1)[1]  # Extract without the first field
    trace_numbers.add(trace_no)
    
    extracted_time = extract_timestamp(entry)

    table_rows.append(
        f"<tr><td>{timestamp}</td><td>{host}</td><td>{source}</td>"
        f"<td>{msg_type}</td><td>{proc_code}</td><td>{resp_code}</td><td>{trace_no}</td>"
        f"<td>{extracted_time}</td><td>{raw_data.replace(extracted_time, '', 1)}</td></tr>"
    )

unique_trace_numbers = ' '.join(map(str, trace_numbers))
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
            text-align: center; /* Center the text */
        }}
    </style>
</head>
<body>

<h2 style="text-align:center;">Trace Table Information({unique_trace_numbers})</h2>
<table>
    <tr>
        <th>Splunk Timestamp</th>
        <th>Host</th>
        <th>Source</th>
        <th>Message Type</th>
        <th>Proc Code</th>
        <th>Resp Code</th>
        <th>Trace No</th>
        <th>Time in PDT</th>
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

print("HTML table is created and saved to output_table.html.")

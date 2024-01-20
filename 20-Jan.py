import json
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

def replace_underscore_with_space(text):
    # Capitalize the first letter of each word
    return ' '.join(word.capitalize() for word in text.split('_'))

try:
    with open(json_file_path, 'r', encoding='utf-8') as file:
        json_content = file.read()
        cleaned_json_content = json.loads(json_content, object_hook=clean_json)
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")
    problematic_part = json_content[e.pos:e.pos + 10]  # Print the problematic part of the JSON
    print(f"Problematic part of JSON: {problematic_part}")
    exit(1)

# Find all unique fields present in the JSON
all_fields = set(field for entry in cleaned_json_content for field in entry)

# Check if there are any required fields present
required_fields = {"_time", "host", "source", "msg_type", "proc_code", "resp_code", "trace_no", "_raw"}
valid_fields = required_fields.intersection(all_fields)

if not valid_fields:
    print("None of the required fields are present. Cannot create HTML table.")
    exit(1)

table_rows = []
trace_numbers = set()

# Dynamic header based on valid fields
custom_header = [replace_underscore_with_space(field) for field in valid_fields]

# Rest of your code using the 'cleaned_json_content' variable
for entry in cleaned_json_content:
    # Dynamically retrieve values only for the fields present in the JSON
    row_values = [entry.get(field, "") for field in valid_fields]

    # Extract trace_no if present
    if "trace_no" in valid_fields:
        trace_numbers.add(entry["trace_no"])

    table_rows.append(
        f"<tr>{''.join(f'<td>{value}</td>' for value in row_values)}</tr>"
    )

# Create a comma-separated string of unique trace numbers
unique_trace_numbers = ', '.join(map(str, trace_numbers)) if "trace_no" in valid_fields else ""

# Create HTML table with dynamic header
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
            text-align: center;  # Updated to center align
            padding: 8px;
        }}
        th {{
            background-color: #f2f2f2;
        }}
    </style>
</head>
<body>

<h2>Trace Table Information</h2>
<table>
    <tr>{''.join(f'<th>{header}</th>' for header in custom_header)}</tr>
    {"".join(table_rows)}
</table>

</body>
</html>
"""

# Write HTML table to a file
with open('output_table.html', 'w') as html_file:
    html_file.write(html_table)

print("HTML table created and saved to output_table.html.")

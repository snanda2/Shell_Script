import re
from collections import deque
import os
import json

def tail(filename, n=10):
    """Read the last n lines from the given file."""
    with open(filename, 'r', errors='replace') as file:
        return deque(file, n)

def clean_line(line):
    """Remove or replace invalid control characters from the line."""
    # Remove characters outside the ASCII printable range
    cleaned_line = ''.join(char if 32 <= ord(char) < 127 else ' ' for char in line)

    # Remove problematic double quotes within double quotes
    cleaned_line = re.sub(r'"(.*?)"', lambda x: x.group().replace('"', ''), cleaned_line)

    # Ensure the line has balanced braces
    while cleaned_line.count('{') > cleaned_line.count('}'):
        cleaned_line = cleaned_line.rsplit('{', 1)[0]

    return cleaned_line


def clean_and_extract_response_fields(line):
    try:
        # Clean the line before attempting to extract response fields
        cleaned_line = clean_line(line)

        # Extracting the JSON part of the line
        json_start = cleaned_line.find('{"')
        json_str = cleaned_line[json_start:]
        json_data = json.loads(json_str)

        # Extracting relevant fields from the JSON data
        response_code = json_data.get('responseCode', 'Not Present')
        response_message = json_data.get('responseMessage', 'Not Present')
        host_response_code = json_data.get('hostResponseCode', 'Not Present')
        actual_response_code = json_data.get('additionalResponseData', {}).get('actualResponseCode', 'Not Present')

        return response_code, response_message, host_response_code, actual_response_code
    except json.JSONDecodeError as json_error:
        print(f"Error decoding JSON: {json_error}")
        print(f"Problematic JSON string: {cleaned_line}")
        return None
    except Exception as e:
        print(f"Error extracting response fields: {e}")
        return None

# Use the Downloads folder as the log_directory
downloads_directory = os.path.join(os.path.expanduser('~'), 'Downloads')

# Ask the user for the date
target_date = input("Enter the date (YYYY-MM-DD): ")

# Find matching log files
matching_files = [os.path.join(downloads_directory, f) for f in os.listdir(downloads_directory) if f.startswith(f'wso2carbon-{target_date}') and f.endswith('.txt')]

# Print found log files
print("\nFound Log Files:")
for log_file in matching_files:
    print(log_file)

while True:
    # Ask the user for options
    print("\nOptions:")
    print("1. Print last 10 lines continuously (default)")
    print("2. Manually enter the number of lines to print")
    print("3. Display all lines")
    print("0. Exit")

    choice = input("Enter your choice (0-3): ")

    if choice == "0":
        break
    elif choice == "1":
        num_lines = 10
    elif choice == "2":
        num_lines_input = input("Enter the number of lines to print: ")
        try:
            num_lines = int(num_lines_input)
        except ValueError:
            print("Invalid input. Please enter a valid number.")
            continue
    elif choice == "3":
        num_lines = None  # Display all lines
    else:
        print("Invalid choice. Please enter 0, 1, 2, or 3.")
        continue

    # Process each matching log file
    for log_file in matching_files:
        print(f"\nLog file: {log_file}")
        lines = tail(log_file, n=num_lines)

        for line in lines:
            response_fields = clean_and_extract_response_fields(line)
            if response_fields:
                response_code, response_message, host_response_code, actual_response_code = response_fields
                print(f"{response_code}\t{response_message}\t{host_response_code}\t{actual_response_code}")

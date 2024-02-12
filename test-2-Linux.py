import os
import json
import re
from collections import Counter

def print_response_fields(response_parts):
    # Print headers
    print("\nResponse Code\tResponse Message\tHost Response Code\tActual Response Code\tPercentage\tTotal Count")

    response_codes = [str(json.loads(part).get('responseCode')) for part in response_parts if part]
    total_counts = Counter(response_codes)
    total_out_messages = len(response_parts)

    for response_code, count in total_counts.items():
        try:
            # Get the first occurrence of the response code
            response_part = next(part for part in response_parts if json.loads(part).get('responseCode') == int(response_code))

            # Attempt to parse the cleaned JSON
            json_data = json.loads(response_part)

            # Extract desired fields
            response_message = str(json_data.get('responseMessage', ''))
            host_response_code = str(json_data.get('hostResponseCode', ''))

            # Extract 'actualResponseCode' from nested structures if present
            actual_response_code = None
            if 'additionalResponseData' in json_data and 'actualResponseCode' in json_data['additionalResponseData']:
                actual_response_code = str(json_data['additionalResponseData']['actualResponseCode'])

            # Provide default values if any field is None
            response_code = response_code if response_code is not None else ''
            response_message = response_message if response_message is not None else ''
            host_response_code = host_response_code if host_response_code is not None else ''
            actual_response_code = actual_response_code if actual_response_code is not None else ''

            # Calculate percentage
            percentage = (count / total_out_messages) * 100

            # Print in the specified format with proper alignment
            print(f"{response_code.ljust(15)}\t{response_message.ljust(25)}\t{host_response_code.ljust(20)}\t{actual_response_code.ljust(20)}\t{percentage:.2f}%\t{count}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {response_part}, {e}")

def process_log_files(directory_path, date):
    in_message_count = 0  # Initialize to 0
    response_parts = []

    # Iterate over all files in the directory
    for filename in os.listdir(directory_path):
        if filename.startswith(f'wso2carbon-{date}') and filename.endswith('.txt'):
            file_path = os.path.join(directory_path, filename)

            try:
                with open(file_path, 'r', errors='replace') as file:
                    inside_response_section = False

                    for line in file:
                        if 'IN_MESSAGE' in line:
                            in_message_count += 1
                        elif 'OUT_MESSAGE' in line and '--- Response ---' in line:
                            response_part = print_after_response(line)
                            if response_part:
                                response_parts.append(response_part)
            except FileNotFoundError:
                print(f"Error: File not found at path {file_path}")
            except Exception as e:
                print(f"Error reading the file: {e}")

    # Print totals
    print(f"\nTotal No. of IN_MESSAGE: {in_message_count}")
    print(f"Total No. of OUT_MESSAGE: {len(response_parts)}")

    # Print response details
    print_response_fields(response_parts)

def print_after_response(line):
    match = re.search(r'--- Response ---\s*=\s*({.+})(?:,\s*messageType\s*=\s*application/json)?\s*$', line)
    if match:
        response_part = match.group(1)

        # Remove non-printable characters
        response_part_cleaned = ''.join(char for char in response_part if char.isprintable())

        return response_part_cleaned

# Directory path and date input
directory_path = '/tmp'
date = input("Enter the date (in the format YYYY-MM-DD): ")

# Process the log files
process_log_files(directory_path, date)

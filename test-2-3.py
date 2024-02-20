import os
import json
import re
from collections import Counter
import time
import socket

def print_response_fields(response_parts):
    # Print headers
    print("\nResponse Code\tResponse Message\tHost Response Code\tActual Response Code\tPercentage\tTotal Count")

    response_parts.sort(key=lambda x: int(x.get('responseCode', 0)) if isinstance(x.get('responseCode'), (int, str)) and str(x.get('responseCode')).isdigit() else 0)
    total_counts = Counter(str(part.get('responseCode', 'NA')) for part in response_parts)

    total_out_messages = len(response_parts)

    for response_code, count in total_counts.items():
        try:
            # Get the first occurrence of the response code
            response_part = next(part for part in response_parts if str(part.get('responseCode', 'NA')) == response_code)

            # Extract desired fields
            if response_code == "4000001":
                response_message = "Msg/Txn Id is Mandatory"
            else:
                response_message = str(response_part.get('responseMessage', ''))

            host_response_code = str(response_part.get('hostResponseCode', 'NA'))

            # Extract 'actualResponseCode' from nested structures if present
            actual_response_code = None
            if 'additionalResponseData' in response_part and 'actualResponseCode' in response_part['additionalResponseData']:
                actual_response_code = str(response_part['additionalResponseData']['actualResponseCode'])

            # Provide default values if any field is None
            response_code = response_code if response_code is not None else ''
            response_message = response_message if response_message is not None else ''
            host_response_code = host_response_code if host_response_code is not None else 'NA'
            actual_response_code = actual_response_code if actual_response_code is not None else ''

            # Calculate percentage
            percentage = (count / total_out_messages) * 100

            # Print in the specified format with proper alignment
            print(f"{response_code.ljust(15)}\t{response_message.ljust(25)}\t{host_response_code.ljust(20)}\t{actual_response_code.ljust(20)}\t{percentage:.2f}%\t{count}")
        except StopIteration:
            print(f"Error: No response part found for response code {response_code}")

def process_log_files(directory_path, date):
    # Start the timer
    start_time = time.time()
    # Initialize to 0
    in_message_count = 0
    response_parts = []

    # Counter for total messages and messages with certificates
    total_out_messages = 0
    total_out_messages_with_certificate = 0

    # Set to store unique response codes
    unique_response_codes = set()

    # Function to extract response part
    def print_after_response(line):
        match = re.search(r'--- Response ---\s*=\s*({.+})(?:,\s*messageType\s*=\s*application/json)?\s*$', line)
        if match:
            response_part = match.group(1)

            # Remove non-printable characters
            response_part_cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', response_part)

            try:
                # Attempt to parse the cleaned JSON
                json_data = json.loads(response_part_cleaned)

                return json_data
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {response_part_cleaned}, {e}")
                return None

    # Function to extract OUT_MESSAGE and response details from the same line
    def process_combined_line(line):
        # Extract OUT_MESSAGE details
        match_out_message = re.search(r'TXN = OUT_MESSAGE(?:,|$)', line)
        if match_out_message:
            uuid_match = re.search(r'UUID = (\S+)', line)
            if uuid_match:
                uuid = uuid_match.group(1)

                # Check if there are response details in the same line
                response_part = print_after_response(line)
                if response_part is not None:
                    if "certificate" not in line:
                        response_parts.append(response_part)
                    else:
                        total_out_messages_with_certificate += 1
                        unique_response_codes.add(response_part.get('responseCode', '0'))

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
                            total_out_messages += 1

                            response_part = print_after_response(line)
                            if response_part is not None:
                                if "certificate" not in line:
                                    response_parts.append(response_part)
                                else:
                                    total_out_messages_with_certificate += 1
                                    unique_response_codes.add(response_part.get('responseCode', '0'))
                        elif 'TXN = OUT_MESSAGE' in line:
                            # Process OUT_MESSAGE and response details from the same line
                            process_combined_line(line)

            except FileNotFoundError:
                print(f"Error: File not found at path {file_path}")
            except Exception as e:
                print(f"Error reading the file: {e}")

    # Print hostname
    hostname = socket.gethostname()
    print(f"\nExecuting on hostname: {hostname}")

    # Print totals
    print(f"\nTotal No. of IN_MESSAGE: {in_message_count}")
    print(f"Total No. of OUT_MESSAGE: {total_out_messages}")

    # Print dropped message percentage if applicable
    if in_message_count > total_out_messages:
        dropped_message_percentage = ((in_message_count - total_out_messages) / in_message_count) * 100
        print(f"Dropped MESSAGE Percentage: {dropped_message_percentage:.2f}%")

    print(f"Total No. of OUT_MESSAGE that contains certificate: {total_out_messages_with_certificate}")

    # Print response details
    print_response_fields(response_parts)

    # Stop the timer
    end_time = time.time()
    elapsed_time = end_time - start_time
    script_name = os.path.basename(__file__)
    print(f"\nScript '{script_name}' completed in {elapsed_time:.2f} seconds.")

# Directory path and date input
directory_path = os.path.join(os.path.expanduser('~'), 'Downloads')
date = input("Enter the date (in the format YYYY-MM-DD): ")

# Process the log files
process_log_files(directory_path, date)

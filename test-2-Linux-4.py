import os
import json
import re
from collections import Counter
import time
import socket
from datetime import datetime

def is_valid_date(date):
    try:
        datetime.strptime(date, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def is_valid_time(time_str):
    try:
        datetime.strptime(time_str, '%H:%M:%S')
        return True
    except ValueError:
        return False

def extract_time(log_line):
    match = re.search(r'\[.*?\] \[.*?\] \[([\d\s,-:]+)\]', log_line)
    if match:
        timestamp = match.group(1)
        time_only = re.search(r'(\d+:\d+:\d+)', timestamp)
        if time_only:
            return time_only.group(1)
    return None

def extract_records_in_time_range(file_path, target_date, start_time, end_time):
    start_datetime = datetime.strptime(f"{target_date} {start_time}", "%Y-%m-%d %H:%M:%S")
    end_datetime = datetime.strptime(f"{target_date} {end_time}", "%Y-%m-%d %H:%M:%S")

    matching_lines = []
    with open(file_path, 'r', errors='replace') as file:
        for line_number, line in enumerate(file, start=1):
            log_time = extract_time(line)
            if log_time:
                log_datetime = datetime.strptime(f"{target_date} {log_time}", "%Y-%m-%d %H:%M:%S")
                if start_datetime <= log_datetime <= end_datetime:
                    matching_lines.append(f"{line.strip()}")

    return matching_lines

def print_response_fields(response_parts):

    print("\nResponse Code\tResponse Message\tHost Response Code\tActual Response Code\t\tPercentage\tTotal Count")

    response_parts.sort(key=lambda x: int(x.get('responseCode', 0)) if isinstance(x.get('responseCode'), (int, str)) and str(x.get('responseCode')).isdigit() else 0)
    total_counts = Counter(str(part.get('responseCode', 'NA')) for part in response_parts)

    total_out_messages = len(response_parts)

    for response_code, count in total_counts.items():
        try:
            
            response_part = next(part for part in response_parts if str(part.get('responseCode', 'NA')) == response_code)

            if response_code == "4000001":
                response_message = "Msg/Txn Id is Mandatory"
            else:
                response_message = str(response_part.get('responseMessage', ''))

            host_response_code = str(response_part.get('hostResponseCode', 'NA'))
            additional_response_data = response_part.get('additionalResponseData', {})
            actual_response_code = additional_response_data.get('actualResponseCode', 'NA')

            if not actual_response_code.strip():
                actual_response_code = 'NA'

            response_code = response_code if response_code is not None else ''
            response_message = response_message if response_message is not None else ''
            host_response_code = host_response_code if host_response_code is not None else 'NA'
            actual_response_code = actual_response_code if actual_response_code is not None else 'NA'
            percentage = (count / total_out_messages) * 100

            print(f"{response_code.ljust(15)}\t{response_message.ljust(25)}\t{host_response_code.ljust(20)}\t{actual_response_code.ljust(20)}\t{percentage:.2f}%\t\t{count}")
        except StopIteration:
            print(f"Error: No response part found for response code {response_code}")

def process_log_files(directory_path, date):
    if not is_valid_date(date):
        print("Invalid date entered. Exiting.")
        return
    elif datetime.strptime(date, '%Y-%m-%d').date() > datetime.now().date():
        print("Future date entered. Exiting.")
        return
    else:
        start_time = time.time()
        in_message_count = 0
        response_parts = []
        total_out_messages = 0
        total_out_messages_with_certificate = 0

        unique_response_codes = set()

        def print_after_response(line):
            match = re.search(r'--- Response ---\s*=\s*({.+})(?:,\s*messageType\s*=\s*application/json)?\s*$', line)
            if match:
                response_part = match.group(1)

                response_part_cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', response_part)

                try:
                    json_data = json.loads(response_part_cleaned)

                    return json_data
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {response_part_cleaned}, {e}")
                    return None

        def process_combined_line(line):
            match_out_message = re.search(r'TXN = OUT_MESSAGE(?:,|$)', line)
            if match_out_message:
                uuid_match = re.search(r'UUID = (\S+)', line)
                if uuid_match:
                    uuid = uuid_match.group(1)
                    response_part = print_after_response(line)
                    if response_part is not None:
                        if "certificate" not in line:
                            response_parts.append(response_part)
                        else:
                            total_out_messages_with_certificate += 1
                            unique_response_codes.add(response_part.get('responseCode', '0'))


        for filename in os.listdir(directory_path):
            if filename.startswith(f'wso2carbon-{date}') and filename.endswith('.log'):
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
                                process_combined_line(line)

                except FileNotFoundError:
                    print(f"Error: File not found at path {file_path}")
                except Exception as e:
                    print(f"Error reading the file: {e}")

        hostname = socket.gethostname()
        print(f"\nExecuting on hostname: {hostname}")

        print(f"\nTotal No. of IN_MESSAGE: {in_message_count}")
        print(f"Total No. of OUT_MESSAGE: {total_out_messages}")

        if in_message_count > total_out_messages:
            dropped_message_percentage = ((in_message_count - total_out_messages) / in_message_count) * 100
            print(f"Dropped MESSAGE Percentage: {dropped_message_percentage:.2f}%")

        print(f"Total No. of OUT_MESSAGE that contains certificate: {total_out_messages_with_certificate}")

        print_response_fields(response_parts)

        end_time = time.time()
        elapsed_time = end_time - start_time
        script_name = os.path.basename(__file__)
        print(f"\nScript '{script_name}' completed in {elapsed_time:.2f} seconds.")

def extract_logs_in_time_range(directory_path, date, start_time, end_time):
    if not is_valid_date(date):
        print("Invalid date entered. Exiting.")
        return
    elif datetime.strptime(date, '%Y-%m-%d').date() > datetime.now().date():
        print("Future date entered. Exiting.")
        return
    elif not is_valid_time(start_time) or not is_valid_time(end_time):
        print("Invalid time format entered. Exiting.")
        return
    else:
        start_time_total = time.time()
        in_message_count = 0
        response_parts = []
        total_out_messages = 0
        total_out_messages_with_certificate = 0
        unique_response_codes = set()

        def print_after_response(line):
            match = re.search(r'--- Response ---\s*=\s*({.+})(?:,\s*messageType\s*=\s*application/json)?\s*$', line)
            if match:
                response_part = match.group(1)
                response_part_cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', response_part)

                try:
                    json_data = json.loads(response_part_cleaned)

                    return json_data
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {response_part_cleaned}, {e}")
                    return None

        def process_combined_line(line):
            match_out_message = re.search(r'TXN = OUT_MESSAGE(?:,|$)', line)
            if match_out_message:
                uuid_match = re.search(r'UUID = (\S+)', line)
                if uuid_match:
                    uuid = uuid_match.group(1)e
                    response_part = print_after_response(line)
                    if response_part is not None:
                        if "certificate" not in line:
                            response_parts.append(response_part)
                        else:
                            total_out_messages_with_certificate += 1
                            unique_response_codes.add(response_part.get('responseCode', '0'))

        for filename in os.listdir(directory_path):
            if filename.startswith(f'wso2carbon-{date}') and filename.endswith('.log'):
                file_path = os.path.join(directory_path, filename)

                try:
                    with open(file_path, 'r', errors='replace') as file:
                        inside_response_section = False

                        for line in file:
                            log_time = extract_time(line)
                            if log_time:
                                log_datetime = datetime.strptime(f"{date} {log_time}", "%Y-%m-%d %H:%M:%S")
                                start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
                                end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")

                                if start_datetime <= log_datetime <= end_datetime:
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
                                        process_combined_line(line)

                except FileNotFoundError:
                    print(f"Error: File not found at path {file_path}")
                except Exception as e:
                    print(f"Error reading the file: {e}")

        hostname = socket.gethostname()
        print(f"\nExecuting on hostname: {hostname}")

        print(f"\nTotal No. of IN_MESSAGE: {in_message_count}")
        print(f"Total No. of OUT_MESSAGE: {total_out_messages}")

        if in_message_count > total_out_messages:
            dropped_message_percentage = ((in_message_count - total_out_messages) / in_message_count) * 100
            print(f"Dropped MESSAGE Percentage: {dropped_message_percentage:.2f}%")

        print(f"Total No. of OUT_MESSAGE that contains certificate: {total_out_messages_with_certificate}")
        print_response_fields(response_parts)

        end_time_total = time.time()
        elapsed_time_total = end_time_total - start_time_total
        script_name = os.path.basename(__file__)
        print(f"\nScript '{script_name}' completed in {elapsed_time_total:.2f} seconds.")

# Directory path and date input
directory_path = '/home/sukumar/temp'
date = input("Enter the date (in the format YYYY-MM-DD): ")

use_time_range = input("Do you want to specify a time range? (yes/no): ").lower()
if use_time_range == 'yes':
    start_time = input("Enter the start time (HH:MM:SS): ")
    end_time = input("Enter the end time (HH:MM:SS): ")
    extract_logs_in_time_range(directory_path, date, start_time, end_time)
else:
    process_log_files(directory_path, date)

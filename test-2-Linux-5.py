#!/usr/bin/env python3

import os
import json
import re
import tarfile
from collections import defaultdict, Counter
import time
import socket
from datetime import datetime

# Define path variables
LOG_DIRECTORY_TODAY = '/data/wso2/wso2am-3.2.0/repository/logs'
BACKUP_DIRECTORY_TEMPLATE = '/ist-shared/backup/{}/backup_wso2'
ARCHIVE_FILE_NAME = 'bkd_archive.tgz'
EXTRACTED_DIR_NAME = 'extracted'

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

def print_response_fields(response_parts):
    print("\nResponse Code\tResponse Message\tHost Response Code\tPercentage\tTotal Count")

    response_dict = defaultdict(lambda: defaultdict(int))
    total_counts = Counter()

    for part in response_parts:
        response_code = str(part.get('responseCode', 'NA'))
        response_message = "Msg/Txn Id is Mandatory" if response_code == "4000001" else str(part.get('responseMessage', ''))
        host_response_code = str(part.get('hostResponseCode', 'NA')).strip()

        # Normalize host response code for response code 0
        if response_code == "0":
            if host_response_code not in ["002", "02"]:
                host_response_code = "00"
                response_message = "Transactions Authorized"

        key = (response_message, host_response_code)
        response_dict[response_code][key] += 1
        total_counts[response_code] += 1

    total_out_messages = len(response_parts)
    total_successful_transactions = total_counts.get("0", 0)
    total_failure_transactions = total_out_messages - total_successful_transactions

    cis_decline_count = 0
    non_cis_decline_count = 0

    for response_code, count in total_counts.items():
        if response_code != "0":
            for key, sub_count in response_dict[response_code].items():
                response_message, host_response_code = key
                if response_code == "91" or (response_code == "8" and host_response_code == "905"):
                    cis_decline_count += sub_count
                else:
                    non_cis_decline_count += sub_count

    sorted_response_codes = sorted(response_dict.keys(), key=lambda x: (int(x) if x.isdigit() else float('inf')))

    for response_code in sorted_response_codes:
        message_dict = response_dict[response_code]
        sorted_entries = sorted(message_dict.items(), key=lambda item: item[1], reverse=True)
        for key, count in sorted_entries:
            response_message, host_response_code = key
            percentage = (count / total_out_messages) * 100
            print(f"{response_code.ljust(15)}\t{response_message.ljust(25)}\t{host_response_code.ljust(20)}\t{percentage:.2f}%\t\t{count}")

    print(f"\nTotal Transactions Count: {total_out_messages}")
    print(f"Total Successful Transactions Count: {total_successful_transactions}")
    print(f"Total Failure Transactions Count: {total_failure_transactions}")
    print(f"CIS Decline Count: {cis_decline_count}")
    print(f"Non-CIS Decline Count: {non_cis_decline_count}")

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

def process_combined_line(line, response_parts, total_out_messages_with_certificate, unique_response_codes):
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

def process_log_file(file_path, date, response_parts, total_out_messages_with_certificate, unique_response_codes, start_time=None, end_time=None):
    in_message_count = 0
    total_out_messages = 0
    earliest_time = None
    latest_time = None

    try:
        with open(file_path, 'r', errors='replace') as file:
            for line in file:
                log_time = extract_time(line)
                if log_time:
                    log_datetime = datetime.strptime(f"{date} {log_time}", "%Y-%m-%d %H:%M:%S")
                    if earliest_time is None or log_datetime < earliest_time:
                        earliest_time = log_datetime
                    if latest_time is None or log_datetime > latest_time:
                        latest_time = log_datetime

                    if start_time and end_time:
                        start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
                        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")
                        if not (start_datetime <= log_datetime <= end_datetime):
                            continue

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
                    process_combined_line(line, response_parts, total_out_messages_with_certificate, unique_response_codes)

    except FileNotFoundError:
        print(f"Error: File not found at path {file_path}")
    except Exception as e:
        print(f"Error reading the file: {e}")

    return in_message_count, total_out_messages, earliest_time, latest_time

def extract_tar_file(tar_path, extract_to):
    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(path=extract_to)
    except Exception as e:
        print(f"Error extracting tar file {tar_path}: {e}")

def find_log_files_in_archives(archive_dir, date, log_files):
    for archive_folder in os.listdir(archive_dir):
        if archive_folder.startswith(f'archive-{date.replace("-", "")}'):
            folder_path = os.path.join(archive_dir, archive_folder)
            tar_file_path = os.path.join(folder_path, ARCHIVE_FILE_NAME)
            if os.path.exists(tar_file_path):
                extract_to = os.path.join(folder_path, EXTRACTED_DIR_NAME)
                os.makedirs(extract_to, exist_ok=True)
                extract_tar_file(tar_file_path, extract_to)
                for log_file in os.listdir(extract_to):
                    if log_file.startswith(f'wso2carbon-{date}'):
                        log_files.append(os.path.join(extract_to, log_file))

def process_log_files(date, original_hostname, start_time=None, end_time=None):
    if not is_valid_date(date):
        print("Invalid date entered. Exiting.")
        return
    elif datetime.strptime(date, '%Y-%m-%d').date() > datetime.now().date():
        print("Future date entered. Exiting.")
        return

    start_time_total = time.time()
    response_parts = []
    total_out_messages_with_certificate = 0
    unique_response_codes = set()

    in_message_count = 0
    total_out_messages = 0
    overall_earliest_time = None
    overall_latest_time = None

    if datetime.strptime(date, '%Y-%m-%d').date() == datetime.now().date():
        log_files = [os.path.join(LOG_DIRECTORY_TODAY, 'wso2carbon.log')]
    else:
        backup_directories = [
            BACKUP_DIRECTORY_TEMPLATE.format(original_hostname),
            BACKUP_DIRECTORY_TEMPLATE.format(get_alternate_hostname(original_hostname))
        ]
        date_str = date.replace('-', '')
        log_files = []

        # Check backup directories first
        for backup_directory in backup_directories:
            if os.path.exists(backup_directory):
                for backup_folder in os.listdir(backup_directory):
                    if backup_folder.startswith(f'backup-{date_str}'):
                        folder_path = os.path.join(backup_directory, backup_folder)
                        for log_file in os.listdir(folder_path):
                            if log_file.startswith(f'wso2carbon-{date}'):
                                log_files.append(os.path.join(folder_path, log_file))

        # If no log files found in backup directories, check archive directories
        if not log_files:
            for archive_directory in backup_directories:
                find_log_files_in_archives(archive_directory, date, log_files)

    for log_file in log_files:
        inc, out, earliest_time, latest_time = process_log_file(log_file, date, response_parts, total_out_messages_with_certificate, unique_response_codes, start_time, end_time)
        in_message_count += inc
        total_out_messages += out
        if earliest_time and (overall_earliest_time is None or earliest_time < overall_earliest_time):
            overall_earliest_time = earliest_time
        if latest_time and (overall_latest_time is None or latest_time > overall_latest_time):
            overall_latest_time = latest_time

    hostname = socket.gethostname()
    print(f"\nExecuting on hostname: {hostname}")
    print(f"\nTotal No. of IN_MESSAGE: {in_message_count}")
    print(f"Total No. of OUT_MESSAGE: {total_out_messages}")

    if in_message_count > total_out_messages:
        dropped_message_percentage = ((in_message_count - total_out_messages) / in_message_count) * 100
        if dropped_message_percentage > 0:
            print(f"Dropped MESSAGE Percentage: {dropped_message_percentage:.2f}%")

    if total_out_messages_with_certificate > 0:
        print(f"Total No. of OUT_MESSAGE that contains certificate: {total_out_messages_with_certificate}")

    if overall_earliest_time:
        print(f"\nStart Time: {overall_earliest_time.strftime('%Y-%m-%d %H:%M:%S')}")
    if overall_latest_time:
        print(f"End Time: {overall_latest_time.strftime('%Y-%m-%d %H:%M:%S')}")

    print_response_fields(response_parts)

    end_time_total = time.time()
    elapsed_time_total = end_time_total - start_time_total
    script_name = os.path.basename(__file__)
    print(f"\nScript '{script_name}' completed in {elapsed_time_total:.2f} seconds.")

def get_alternate_hostname(hostname):
    if hostname.endswith('01'):
        return hostname[:-2] + '02'
    elif hostname.endswith('02'):
        return hostname[:-2] + '01'
    else:
        raise ValueError("Hostname does not end in '01' or '02'")

def main():
    original_hostname = socket.gethostname()

    today = input("Is it today's date? (yes/no): ").strip().lower()
    if today == 'yes':
        date = datetime.now().strftime('%Y-%m-%d')
    else:
        date = input("Enter the date (in the format YYYY-MM-DD): ").strip()
        if not is_valid_date(date):
            print("Invalid date format. Exiting.")
            return
        if datetime.strptime(date, '%Y-%m-%d').date() > datetime.now().date():
            print("Future date entered. Exiting.")
            return

    use_time_range = input("Do you want to specify a time range? (yes/no): ").strip().lower()
    if use_time_range == 'yes':
        start_time = input("Enter the start time (HH:MM:SS): ").strip()
        end_time = input("Enter the end time (HH:MM:SS): ").strip()
        if not is_valid_time(start_time) or not is_valid_time(end_time):
            print("Invalid time format. Exiting.")
            return
        process_log_files(date, original_hostname, start_time, end_time)
    else:
        process_log_files(date, original_hostname)

if __name__ == "__main__":
    main()

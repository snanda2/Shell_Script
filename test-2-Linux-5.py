import os
import json
import re
import tarfile
import argparse
from collections import Counter
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
    print("\nResponse Code\tResponse Message\tHost Response Code\tActual Response Code\t\tPercentage\tTotal Count")

    response_parts.sort(key=lambda x: int(x.get('responseCode', 0)) if isinstance(x.get('responseCode'), (int, str)) and str(x.get('responseCode')).isdigit() else 0)
    total_counts = Counter(str(part.get('responseCode', 'NA')) for part in response_parts)
    total_out_messages = len(response_parts)

    for response_code, count in total_counts.items():
        try:
            response_part = next(part for part in response_parts if str(part.get('responseCode', 'NA')) == response_code)
            response_message = "Msg/Txn Id is Mandatory" if response_code == "4000001" else str(response_part.get('responseMessage', ''))
            host_response_code = str(response_part.get('hostResponseCode', 'NA'))
            actual_response_code = response_part.get('additionalResponseData', {}).get('actualResponseCode', 'NA')
            actual_response_code = actual_response_code if actual_response_code.strip() else 'NA'

            percentage = (count / total_out_messages) * 100

            print(f"{response_code.ljust(15)}\t{response_message.ljust(25)}\t{host_response_code.ljust(20)}\t{actual_response_code.ljust(20)}\t{percentage:.2f}%\t\t{count}")
        except StopIteration:
            print(f"Error: No response part found for response code {response_code}")

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

    try:
        with open(file_path, 'r', errors='replace') as file:
            for line in file:
                log_time = extract_time(line)
                if start_time and end_time and log_time:
                    log_datetime = datetime.strptime(f"{date} {log_time}", "%Y-%m-%d %H:%M:%S")
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

    return in_message_count, total_out_messages

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
        inc, out = process_log_file(log_file, date, response_parts, total_out_messages_with_certificate, unique_response_codes, start_time, end_time)
        in_message_count += inc
        total_out_messages += out

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

def get_alternate_hostname(hostname):
    if hostname.endswith('01'):
        return hostname[:-2] + '02'
    elif hostname.endswith('02'):
        return hostname[:-2] + '01'
    else:
        raise ValueError("Hostname does not end in '01' or '02'")

def main():
    parser = argparse.ArgumentParser(description="Process log files for WSO2.")
    parser.add_argument('-d', '--date', type=str, help="Specify the date (format: YYYY-MM-DD).")
    parser.add_argument('-t', '--time', nargs=2, metavar=('START_TIME', 'END_TIME'), help="Specify the start and end times (format: HH:MM:SS).")
    
    args = parser.parse_args()
    original_hostname = socket.gethostname()

    if args.date:
        if not is_valid_date(args.date):
            print("Invalid date format. Please use YYYY-MM-DD.")
            return
        if datetime.strptime(args.date, '%Y-%m-%d').date() > datetime.now().date():
            print("Future date entered. Exiting.")
            return

        if args.time:
            if not (is_valid_time(args.time[0]) and is_valid_time(args.time[1])):
                print("Invalid time format. Please use HH:MM:SS.")
                return
            process_log_files(args.date, original_hostname, args.time[0], args.time[1])
        else:
            process_log_files(args.date, original_hostname)
    else:
        if args.time:
            if not (is_valid_time(args.time[0]) and is_valid_time(args.time[1])):
                print("Invalid time format. Please use HH:MM:SS.")
                return
            process_log_files(datetime.now().strftime('%Y-%m-%d'), original_hostname, args.time[0], args.time[1])
        else:
            process_log_files(datetime.now().strftime('%Y-%m-%d'), original_hostname)

if __name__ == "__main__":
    main()

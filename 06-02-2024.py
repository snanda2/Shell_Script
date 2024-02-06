import re
from collections import deque
import time
import os

def tail(filename, n=10):
    """Read the last n lines from the given file."""
    with open(filename, 'r') as file:
        return deque(file, n)

def extract_response_fields(log_line):
    """Extract response fields from OUT_MESSAGE log line."""
    pattern = re.compile(r'"responseCode":(\d+),"responseMessage":"([^"]*)","hostResponseCode":"([^"]*)","actualResponseCode":"([^"]*)"')
    match = re.search(pattern, log_line)
    if match:
        response_code = match.group(1)
        response_message = match.group(2) if match.group(2) else "Not Present"
        host_response_code = match.group(3) if match.group(3) else "Not Present"
        actual_response_code = match.group(4) if match.group(4) else "Not Present"
        return response_code, response_message, host_response_code, actual_response_code
    else:
        return "Not Present", "Not Present", "Not Present", "Not Present"

def find_matching_log_files(log_directory, target_date):
    """Find log files in the directory with the target date in the filename."""
    matching_files = []
    for filename in os.listdir(log_directory):
        if filename.startswith(f'wso2carbon-{target_date}') and filename.endswith('.log'):
            matching_files.append(os.path.join(log_directory, filename))
    return matching_files

log_directory = '/path/to/log/files/'  # Replace with the actual path

# Ask the user for the date
target_date = input("Enter the date (YYYY-MM-DD): ")

# Find matching log files
matching_files = find_matching_log_files(log_directory, target_date)

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
        # Read the last 'num_lines' lines
        lines = tail(log_file, n=num_lines)

        # Process the filtered lines
        for line in lines:
            if 'OUT_MESSAGE' in line:
                response_code, response_message, host_response_code, actual_response_code = extract_response_fields(line)
                print(f"{response_code}\t{response_message}\t{host_response_code}\t{actual_response_code}")

    # Allow time for the user to view the output
    time.sleep(2)  # Adjust the sleep duration as needed

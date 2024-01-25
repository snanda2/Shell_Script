import re
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Process transaction log file.')
    parser.add_argument('-d', '--date', default=None,
                        help='Specify date in the format yy.mm.dd.')
    parser.add_argument('-s', '--start_time', default=None,
                        help='Specify start time in HH:MM:SS format.')
    parser.add_argument('-e', '--end_time', default=None,
                        help='Specify end time in HH:MM:SS format.')
    return parser.parse_args()

def get_date():
    date = input("Enter date (yy.mm.dd): ")
    return date

def get_time(prompt):
    time = input(prompt)
    return time

def filter_log_file(log_file, date, start_time, end_time):
    with open(log_file, 'r') as file:
        lines = file.readlines()

    filtered_lines = []
    for line in lines:
        if re.search(r'\b' + re.escape(date) + r'\b', line):
            timestamp_str = re.search(r'\d{2}.\d{2}.\d{2} \d{2}:\d{2}:\d{2}.\d{9}', line)
            if timestamp_str:
                timestamp = timestamp_str.group()
                current_time = timestamp[9:17]
                if start_time <= current_time <= end_time and re.search(r'I-SHC-030010: Route: (m0110|m0210|m0120|m0410)', line):
                    filtered_lines.append(line)

    return filtered_lines

def count_response_code_occurrences(lines, response_code):
    count = 0
    for line in lines:
        count += len(re.findall(response_code, line))
    return count

def main():
    args = parse_args()

    if args.date is None:
        date = get_date()
    else:
        date = args.date

    if args.start_time is None:
        start_time = get_time("Enter start time (HH:MM:SS): ")
    else:
        start_time = args.start_time

    if args.end_time is None:
        end_time = get_time("Enter end time (HH:MM:SS): ")
    else:
        end_time = args.end_time

    log_file = r'C:\Users\admin\Downloads\shc.txt'  # Replace with the actual path to your log file
    print(f"Searching for lines for date {date} and time range {start_time} - {end_time}...\n")

    filtered_lines = filter_log_file(log_file, date, start_time, end_time)

    if not filtered_lines:
        print("No lines found for the specified date and time range.")
    else:
        print("Lines containing patterns like 'I-SHC-030010: Route: m0110', 'I-SHC-030010: Route: m0210', 'I-SHC-030010: Route: m0120', 'I-SHC-030010: Route: m0410':")
        for line in filtered_lines:
            print(line, end='')

        total_transactions = len(filtered_lines)

        # Count occurrences of specific response codes
        response_codes = ['00', '01', '02', '03', '04', '05', '06', '07', '10', '11', '12', '13', '14', '15', '19', '21', '25', '28', '39', '41', '42', '51']
        response_code_counts = {code: count_response_code_occurrences(filtered_lines, fr'r{code}') for code in response_codes if count_response_code_occurrences(filtered_lines, fr'r{code}') > 0}

        # Response code descriptions
        response_code_descriptions = {
            '00': 'Approved and completed successfully',
            '01': 'Refer to card issuer',
            '02': 'Refer to card issuer, special condition',
            '03': 'Invalid merchant',
            '04': 'Pick up card (no fraud)',
            '05': 'Do not honor',
            '06': 'Error',
            '07': 'Pick up card, special condition (fraud account)',
            '10': 'Partial approval',
            '11': 'Approved (V.I.P)',
            '12': 'Invalid transaction',
            '13': 'Invalid amount or currency conversion field overflow',
            '14': 'Invalid account number (no such number)',
            '15': 'No such issuer',
            '19': 'Re-enter transaction',
            '21': 'No action taken',
            '25': 'Unable to locate record in file',
            '28': 'File temporarily not available for update or inquiry',
            '39': 'No credit account',
            '41': 'Lost card, pick up (fraud account)',
            '42': 'Stolen card, pick up (fraud account)',
            '51': 'Not sufficient funds'
        }

        # Print results
        print(f"\nTotal Financial Transactions: {total_transactions}")
        
        # Count occurrences of m0410 pattern
        count_m0410 = len([line for line in filtered_lines if 'I-SHC-030010: Route: m0410' in line])
        
        # Display Reversal count
        print(f"Reversal: {count_m0410}")

        print("Total occurrences of specific response codes:")
        for code, count in response_code_counts.items():
            print(f"Response Code {code} ({response_code_descriptions[code]}): {count} occurrences")

        # Calculate percentage for each response code
        print("\nPercentage of specific response codes:")
        for code, count in response_code_counts.items():
            percentage = (count / total_transactions) * 100
            print(f"Response Code {code} ({response_code_descriptions[code]}): {percentage:.2f}%")

if __name__ == "__main__":
    main()

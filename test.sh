#!/bin/bash

function parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -d|--date)
                date=$2
                shift 2
                ;;
            -s|--start_time)
                start_time=$2
                shift 2
                ;;
            -e|--end_time)
                end_time=$2
                shift 2
                ;;
            *)
                echo "Invalid option: $1"
                exit 1
                ;;
        esac
    done
}

function get_date() {
    while true; do
        read -p "Enter date (yy.mm.dd): " date_str
        if [[ $date_str =~ ^[0-9]{2}\.[0-9]{2}\.[0-9]{2}$ ]]; then
            date_obj=$(date -d "$date_str" 2>/dev/null)
            if [ $? -eq 0 ] && [ "$date_obj" != "" ]; then
                now=$(date +%s)
                date_sec=$(date -d "$date_obj" +%s)
                if [ $date_sec -le $now ]; then
                    date=$date_str
                    break
                else
                    echo "Please enter today's date or a past date."
                fi
            else
                echo "Invalid date format. Please use yy.mm.dd."
            fi
        else
            echo "Invalid date format. Please use yy.mm.dd."
        fi
    done
}

function get_time() {
    read -p "$1" time
}

function filter_log_file() {
    while IFS= read -r line; do
        if [[ $line =~ \b$date\b ]]; then
            timestamp_str=$(echo "$line" | grep -E -o '\d{2}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}\.\d{9}')
            if [ "$timestamp_str" != "" ]; then
                timestamp=${timestamp_str}
                current_time=${timestamp:9:17}
                if [[ $start_time <= $current_time && $current_time <= $end_time && $line =~ /m[0-9]{4}|m[0-9]{4} ]]; then
                    filtered_lines+=("$line")
                fi
            fi
        fi
    done < "$log_file"
}

function count_response_code_occurrences() {
    count=0
    for line in "${filtered_lines[@]}"; do
        count=$((count + $(echo "$line" | grep -o "$1" | wc -l)))
    done
}

function main() {
    parse_args "$@"

    if [ -z "$date" ]; then
        get_date
    fi

    if [ -z "$start_time" ]; then
        get_time "Enter start time (HH:MM:SS): "
    fi

    if [ -z "$end_time" ]; then
        get_time "Enter end time (HH:MM:SS): "
    fi

    log_file='/path/to/your/log/file.txt'  # Replace with the actual path to your log file
    echo "Searching for lines for date $date and time range $start_time - $end_time..."

    filter_log_file
    if [ ${#filtered_lines[@]} -eq 0 ]; then
        echo "No lines found for the specified date and time range."
    else
        response_codes=('00' '01' '02' '03' '04' '05' '06' '07' '10' '11' '12' '13' '14' '15' '19' '21' '25' '28' '39' '41' '42' '51')

        declare -A response_descriptions
        response_descriptions['00']='Approved and completed successfully'
        response_descriptions['01']='Refer to card issuer'
        response_descriptions['02']='Refer to card issuer, special condition'
        response_descriptions['03']='Invalid merchant'
        response_descriptions['04']='Pick up card (no fraud)'
        response_descriptions['05']='Do not honor'
        response_descriptions['06']='Error'
        response_descriptions['07']='Pick up card, special condition (fraud account)'
        response_descriptions['10']='Partial approval'
        response_descriptions['11']='Approved (V.I.P)'
        response_descriptions['12']='Invalid transaction'
        response_descriptions['13']='Invalid amount or currency conversion field overflow'
        response_descriptions['14']='Invalid account number (no such number)'
        response_descriptions['15']='No such issuer'
        response_descriptions['19']='Re-enter transaction'
        response_descriptions['21']='No action taken'
        response_descriptions['25']='Unable to locate record in file'
        response_descriptions['28']='File temporarily not available for update or inquiry'
        response_descriptions['39']='No credit account'
        response_descriptions['41']='Lost card, pick up (fraud account)'
        response_descriptions['42']='Stolen card, pick up (fraud account)'
        response_descriptions['51']='Not sufficient funds'

        total_transactions=${#filtered_lines[@]}
        echo -e "\nTotal Financial Transactions: $total_transactions"
        echo -e "\nRESPONSE\t\tDESC\t\t\t\t\tNO.Of TRX\tPERCENTAGE"

        for code in "${response_codes[@]}"; do
            count_response_code_occurrences "r$code"
            if [ $count -gt 0 ]; then
                percentage=$(bc -l <<< "scale=2; ($count / $total_transactions) * 100")
                echo -e "$code\t\t\t${response_descriptions[$code]}\t\t$count\t$percentage%"
            fi
        done
    fi
}

main "$@"

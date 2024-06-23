import requests
import time
import json

def fetch_splunk_data():
    try:
        # Splunk credentials and connection details
        splunk_host = 'your_splunk_host'
        splunk_port = 8089
        username = 'your_username'
        password = 'your_password'

        # Base URL for Splunk REST API
        base_url = f"https://{splunk_host}:{splunk_port}"

        # Login to Splunk and get a session key
        auth_url = f"{base_url}/services/auth/login"
        auth_data = {
            'username': username,
            'password': password
        }
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        auth_response.raise_for_status()

        session_key = auth_response.json()['sessionKey']
        headers = {
            'Authorization': f'Splunk {session_key}'
        }

        # Your Splunk query as a raw string
        search_query = '''
            search index=tintuit_ist host=vlinus*pwso* sourcetype=prod_tintuit_ist_switch_carbon_log
            source="/data/wso2/wso2am-3.2.0/repository/log/wso2carbon*.log" "OUT_MESSAGE" AND "reponseMessage"
            AND (NOT hostResponseCode OR "hostResponseCode":"E*")
            | rex field=_raw "responseCode\":\"(?<rc>\d+)"
            | rex field=_raw "statusCode\":\"(?<sc>\d+)"
            | dedup UUID
            | eval date=strftime(_time, "%Y-%m-%d")
            | stats count by rc
        '''

        # Create a search job
        search_url = f"{base_url}/services/search/jobs"
        search_data = {
            'search': search_query,
            'earliest_time': '2023-06-21T12:30:00.000+00:00',
            'latest_time': '2023-06-21T20:30:00.000+00:00',
            'output_mode': 'json'
        }
        search_response = requests.post(search_url, headers=headers, data=search_data, verify=False)
        search_response.raise_for_status()

        # Get the search job SID
        job_sid = search_response.json()['sid']
        print(f"Search job created with SID: {job_sid}")

        # Wait for the job to complete
        job_status_url = f"{base_url}/services/search/jobs/{job_sid}"
        while True:
            status_response = requests.get(job_status_url, headers=headers, verify=False)
            status_response.raise_for_status()

            job_status = status_response.json()['entry'][0]['content']['dispatchState']
            print(f"Job status: {job_status}")
            if job_status == 'DONE':
                break
            time.sleep(2)

        # Retrieve search results
        results_url = f"{base_url}/services/search/jobs/{job_sid}/results"
        results_response = requests.get(results_url, headers=headers, verify=False)
        results_response.raise_for_status()

        results = results_response.json()['results']
        return results

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == '__main__':
    data = fetch_splunk_data()
    if data:
        for item in data:
            print(json.dumps(item, indent=2))
    else:
        print("Failed to retrieve data from Splunk.")

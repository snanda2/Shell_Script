import splunklib.client as client
import splunklib.results as results

def fetch_splunk_data():
    try:
        # Connect to Splunk
        service = client.connect(
            host='your_splunk_host',
            port=8089,
            username='your_username',
            password='your_password'
        )

        # Verify connection
        if not service:
            raise Exception("Connection to Splunk failed")

        # Your Splunk query
        query = "search index=_internal | head 10"

        # Set custom time range and timezone to GMT
        kwargs = {
            'earliest_time': '2023-06-21T12:30:00.000+00:00',  # Specify the start time in GMT
            'latest_time': '2023-06-21T20:30:00.000+00:00',    # Specify the end time in GMT
            'timezone': 'GMT'  # Set the timezone to GMT
        }

        # Run the query
        job = service.jobs.create(query, **kwargs)

        # Wait for the job to complete
        while not job.is_done():
            pass

        # Get the results
        result_stream = job.results()
        reader = results.ResultsReader(result_stream)

        data = []
        for result in reader:
            if isinstance(result, dict):
                data.append(result)
        return data

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == '__main__':
    data = fetch_splunk_data()
    if data:
        for item in data:
            print(item)
    else:
        print("Failed to retrieve data from Splunk.")

import os
import requests
from requests.auth import HTTPBasicAuth
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone

def get_open_issues(jira_url, username, password, project_key):
    # Dummy data for example purposes
    return [
        {
            'key': 'JIRA-1',
            'fields': {
                'status': {'name': 'Open'},
                'assignee': {'displayName': 'John Doe'},
                'summary': 'Issue 1 summary',
                'created': '2024-01-01T12:00:00.000+0000'
            }
        },
        {
            'key': 'JIRA-2',
            'fields': {
                'status': {'name': 'In Progress'},
                'assignee': {'displayName': 'Jane Smith'},
                'summary': 'Issue 2 summary',
                'created': '2023-12-01T12:00:00.000+0000'
            }
        },
        {
            'key': 'JIRA-3',
            'fields': {
                'status': {'name': 'Reopened'},
                'summary': 'Issue 3 summary',
                'created': '2023-11-01T12:00:00.000+0000'
            }
        }
    ]

def send_email(sender_email, sender_password, receiver_email, subject, body, attachment_path=None):
    # Create a multipart message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Attach HTML content to email
    msg.attach(MIMEText(body, 'html'))

    # If an attachment is provided, attach it to the email
    if attachment_path:
        with open(attachment_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {attachment_path}')
        msg.attach(part)

    # Log in to the SMTP server and send email
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())

# Replace these with your Jira and email details
jira_url = "your_jira_url"
username = "your_username"
password = "your_password"
project_keys = ["project_key_1", "project_key_2", "project_key_3"]
sender_email = "your_email@gmail.com"
sender_password = "your_email_password"
receiver_email = "recipient_email@gmail.com"
subject = "Open Issues Report"

# Define column widths
sl_width = 5
jira_number_width = 15
status_width = 20
assignee_width = 20
summary_width = 50
created_date_width = 20

# Check if the HTML file exists and delete it
html_filename = 'open_issues.html'
if os.path.exists(html_filename):
    os.remove(html_filename)
    print(f"Previous HTML file '{html_filename}' deleted.")

# Initialize overall HTML content
html_content = """
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
        }
        .sidenav {
            height: 100%;
            width: 200px;
            position: fixed;
            z-index: 1;
            top: 0;
            left: 0;
            background-color: #111;
            padding-top: 20px;
        }
        .sidenav a {
            padding: 8px 8px 8px 16px;
            text-decoration: none;
            font-size: 18px;
            color: #818181;
            display: block;
        }
        .sidenav a:hover {
            color: #f1f1f1;
        }
        .content {
            margin-left: 220px;
            padding: 20px;
            width: calc(100% - 220px);
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }
        th {
            border: 1px solid black;
            padding: 8px;
            text-align: center;
            background-color: #33FFBE;
            font-weight: bold;
            font-family: Arial, sans-serif;
        }
        td {
            border: 1px solid black;
            padding: 8px;
            text-align: left;
            font-family: Arial, sans-serif;
        }
        a {
            text-decoration: none;
            color: #0000EE;
            cursor: pointer;
        }
        .summary-header {
            font-weight: bold;
            border-top: 2px solid black;
            border-bottom: 1px solid black;
            background-color: #A533FF;
            color: white;
            text-align: center;
            font-family: Arial, sans-serif;
        }
        .green {
            background-color: limegreen;
        }
        .orange {
            background-color: orange;
        }
        .red {
            background-color: red;
        }
        .main-header {
            border: 2px solid #A533FF;
            background-color: #A533FF;
            color: white;
            text-align: center;
            padding: 10px;
            font-size: 24px;
            font-weight: bold;
            font-family: Arial, sans-serif;
        }
        .left-align {
            text-align: left;
        }
        .right-align {
            text-align: right;
        }
        .center-align {
            text-align: center;
        }
    </style>
    <script>
        function showProject(projectKey) {
            var elements = document.getElementsByClassName('project-content');
            for (var i = 0; i < elements.length; i++) {
                elements[i].style.display = 'none';
            }
            document.getElementById(projectKey).style.display = 'block';
        }
    </script>
</head>
<body>
<div class="sidenav">
"""

# Add project keys to side navigation
for project_key in project_keys:
    html_content += f'<a href="javascript:void(0)" onclick="showProject(\'{project_key}\')">{project_key}</a>'

html_content += """
</div>
<div class="content">
"""

# Loop over each project key
for project_key in project_keys:
    open_issues = get_open_issues(jira_url, username, password, project_key)

    if open_issues:
        # Calculate counts for Issue Summary
        open_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'Open')
        in_progress_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'In Progress')
        reopened_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'Reopened')

        # Calculate counts per assignee
        assignee_counts = {}
        unassigned_count = 0
        for issue in open_issues:
            assignee = issue['fields']['assignee']
            if assignee:
                assignee_name = assignee['displayName']
                assignee_counts[assignee_name] = assignee_counts.get(assignee_name, 0) + 1
            else:
                unassigned_count += 1

        sorted_assignees = sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)

        # Add project key content
        html_content += f"""
        <div id="{project_key}" class="project-content" style="display: none;">
        <h1 class="main-header">Jira Open Issues for {project_key}</h1>
        <table>
            <tr class="summary-header"><td colspan="2">Issue Summary</td></tr>
            <tr>
                <td class="left-align">Open</td>
                <td class="left-align">{open_count}</td>
            </tr>
            <tr>
                <td class="left-align">In Progress</td>
                <td class="left-align">{in_progress_count}</td>
            </tr>
            <tr>
                <td class="left-align">Reopened</td>
                <td class="left-align">{reopened_count}</td>
            </tr>
        </table>

        <table>
            <tr class="summary-header"><td colspan="2">Assignee Summary</td></tr>
            <tr>
                <td class="left-align">Assignee</td>
                <td class="left-align">Total</td>
            </tr>
        """

        for assignee, count in sorted_assignees:
            html_content += f"""
            <tr>
                <td class="left-align">{assignee}</td>
                <td class="left-align">{count}</td>
            </tr>
            """

        html_content += f"""
            <tr>
                <td class="left-align">Unassigned</td>
                <td class="left-align">{unassigned_count}</td>
            </tr>
        </table>

        <table>
            <tr>
                <th class="left-align">SL. No</th>
                <th class="left-align">Jira Number</th>
                <th class="left-align">Status</th>
                <th class="left-align">Assignee</th>
                <th class="left-align">Summary</th>
                <th class="left-align">Created Date</th>
                <th class="left-align">Age of Ticket</th>
            </tr>
        """

        # Add rows to HTML content with clickable links
        for index, issue in enumerate(open_issues, start=1):
            jira_number = issue['key'][:jira_number_width]
            status = issue['fields']['status']['name'][:status_width]
            assignee = (issue['fields']['assignee']['displayName'] if 'assignee' in issue['fields'] and issue['fields']['assignee'] else 'Unassigned')[:assignee_width]
            summary = issue['fields']['summary'][:summary_width]
            created_date = datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%d")

            # Calculate age of the ticket
            created_date_dt = datetime.strptime(created_date, "%Y-%m-%d")
            age_of_ticket_days = (datetime.now(timezone.utc) - created_date_dt).days

            # Determine color based on age
            if age_of_ticket_days < 30:
                age_color = 'green'
            elif age_of_ticket_days < 90:
                age_color = 'orange'
            else:
                age_color = 'red'

            # Generate a clickable link for each Jira number
            jira_link = f"<a href='{jira_url}/browse/{jira_number}' target='_blank'>{jira_number}</a>"

            row_html = f"""
                <tr>
                    <td>{index}</td>
                    <td>{jira_link}</td>
                    <td>{status}</td>
                    <td>{assignee}</td>
                    <td>{summary}</td>
                    <td>{created_date}</td>
                    <td class='{age_color}'>{age_of_ticket_days}</td>
                </tr>
            """
            html_content += row_html

        # Close the HTML content for the project key
        html_content += """
        </table>
        </div>
        """

# Add script to show the first project by default
html_content += f"""
<script>
    document.getElementById('{project_keys[0]}').style.display = 'block';
</script>
</div>
</body>
</html>
"""

# Save the HTML content to a file
with open(html_filename, 'w', encoding='utf-8') as html_file:
    html_file.write(html_content)

print(f"HTML file '{html_filename}' created successfully.")

# Send email with HTML content
send_email(sender_email, sender_password, receiver_email, subject, html_content)

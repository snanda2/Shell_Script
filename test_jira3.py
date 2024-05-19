import os
import requests
from requests.auth import HTTPBasicAuth
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import subprocess
from datetime import datetime

def get_open_issues(jira_url, username, password, project_key):
    # Your existing code to fetch issues from Jira
    # This is a placeholder. Replace it with your actual code.
    response = requests.get(f"{jira_url}/rest/api/2/search?jql=project={project_key} AND status in (Open, 'In Progress', Reopened)",
                            auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        return response.json()['issues']
    else:
        return []

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
project_key = "your_project_key"
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

# Get open issues
open_issues = get_open_issues(jira_url, username, password, project_key)

# Count issues based on status
open_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'Open')
in_progress_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'In Progress')
reopened_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'Reopened')

if open_issues:
    # Create HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            table {{
                border-collapse: collapse;
                width: 48%;
                margin-right: 2%;
                float: left;
            }}
            th, td {{
                border: 1px solid black;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            a {{
                text-decoration: none;
                color: #0000EE;
                cursor: pointer;
            }}
            .summary-header {{
                text-align: left;
                font-weight: bold;
                border-top: 2px solid black; /* Add border to the top */
                border-bottom: 1px solid black; /* Add border to the bottom */
            }}
        </style>
    </head>
    <body>
        <table>
            <tr>
                <th colspan="2" class="summary-header">Issue Summary</th>
            </tr>
            <tr>
                <th>Category</th>
                <th>Total</th>
            </tr>
            <tr>
                <td>Open</td>
                <td>{open_count}</td>
            </tr>
            <tr>
                <td>In Progress</td>
                <td>{in_progress_count}</td>
            </tr>
            <tr>
                <td>Reopened</td>
                <td>{reopened_count}</td>
            </tr>
        </table>
        <table>
            <tr>
                <th colspan="2" class="summary-header">Assignee Summary</th>
            </tr>
            <tr>
                <th>Assignee</th>
                <th>Total</th>
            </tr>
    """

    # Count the number of tickets assigned to each assignee
    assignee_counts = {}
    unassigned_count = 0
    for issue in open_issues:
        assignee = issue['fields']['assignee']
        if assignee:
            assignee_name = assignee['displayName']
            assignee_counts[assignee_name] = assignee_counts.get(assignee_name, 0) + 1
        else:
            unassigned_count += 1

    # Add rows to HTML content for assignee summary
    for assignee, count in assignee_counts.items():
        row_html = f"""
            <tr>
                <td>{assignee}</td>
                <td>{count}</td>
            </tr>
        """
        html_content += row_html

    # Add row for unassigned tickets
    row_html = f"""
            <tr>
                <td>Unassigned</td>
                <td>{unassigned_count}</td>
            </tr>
    """
    html_content += row_html

    # Close the assignee summary table
    html_content += """
        </table>
        <table style="clear: both; width: 100%;">
            <tr>
                <th colspan="6">Open Issues</th>
            </tr>
            <tr>
                <th>SL.No</th>
                <th>Jira Number</th>
                <th>Status</th>
                <th>Assignee</th>
                <th>Summary</th>
                <th>Created Date</th>
            </tr>
    """

    # Add rows to HTML content with clickable links
    for index, issue in enumerate(open_issues, start=1):
        jira_number = issue['key'][:jira_number_width]
        status = issue['fields']['status']['name'][:status_width]
        assignee = (issue['fields']['assignee']['displayName'] if 'assignee' in issue['fields'] and issue['fields']['assignee'] else 'Unassigned')[:assignee_width]
        summary = issue['fields']['summary'][:summary_width]
        created_date = datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%d")

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
            </tr>
        """
        html_content += row_html

    # Close the HTML content
    html_content += """
        </table>
    </body>
    </html>
    """

    # Save the HTML content to a file
    with open(html_filename, 'w', encoding='utf-8') as html_file:
        html_file.write(html_content)

    print(f"HTML file '{html_filename}' created successfully.")

    # Send email with HTML content
    send_email(sender_email, sender_password, receiver_email, subject, html_content)
else:
    print("Failed to retrieve open issues.")

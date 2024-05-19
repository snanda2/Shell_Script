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

    # Create HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
            }}
            th {{
                border: 1px solid black;
                padding: 8px;
                text-align: center;
                background-color: #33FFBE;
                font-weight: bold;
                font-family: Arial, sans-serif;
            }}
            td {{
                border: 1px solid black;
                padding: 8px;
                text-align: left;
                font-family: Arial, sans-serif;
            }}
            a {{
                text-decoration: none;
                color: #0000EE;
                cursor: pointer;
            }}
            .summary-header {{
                font-weight: bold;
                border-top: 2px solid black;
                border-bottom: 1px solid black;
                background-color: #A533FF;
                color: white;
                text-align: center;
                font-family: Arial, sans-serif;
            }}
            .green {{
                background-color: limegreen;
            }}
            .orange {{
                background-color: orange;
            }}
            .red {{
                background-color: red;
            }}
            .main-header {{
                border: 2px solid #A533FF;
                background-color: #A533FF;
                color: white;
                text-align: center;
                padding: 10px;
                font-size: 24px;
                font-weight: bold;
                font-family: Arial, sans-serif;
            }}
            .left-align {{
                text-align: left;
            }}
        </style>
    </head>
    <body>
        <h1 class="main-header">Jira Open Issues for {project_key}</h1>
        <table>
            <tr>
                <th class="left-align">SL.No</th>
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
        created_date_str = issue['fields']['created']
        created_date = datetime.strptime(created_date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        age_of_ticket_days = (datetime.now(timezone.utc) - created_date).days

        if age_of_ticket_days < 30:
            age_class = 'green'
        elif age_of_ticket_days < 90:
            age_class = 'orange'
        else:
            age_class = 'red'

        # Generate a clickable link for each Jira number
        jira_link = f"<a href='{jira_url}/browse/{jira_number}' target='_blank'>{jira_number}</a>"

        row_html = f"""
            <tr>
                <td>{index}</td>
                <td>{jira_link}</td>
                <td>{status}</td>
                <td>{assignee}</td>
                <td>{summary}</td>
                <td>{created_date.strftime("%Y-%m-%d")}</td>
                <td class='{age_class}'>{age_of_ticket_days} days</td>
            </tr>
        """
        html_content += row_html

    # Close the HTML content for the open issues table
    html_content += """
        </table>
    """

    # Add Issue Summary table
    html_content += f"""
        <table>
            <tr>
                <th colspan="2" class="summary-header">Issue Summary</th>
            </tr>
            <tr>
                <th class="left-align">Category</th>
                <th class="left-align">Total</th>
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
    """

    # Add Assignee Summary table
    html_content += """
        <table>
            <tr>
                <th colspan="2" class="summary-header">Assignee Summary</th>
            </tr>
            <tr>
                <th class="left-align">Assignee</th>
                <th class="left-align">Total</th>
            </tr>
    """

    for assignee, count in sorted_assignees:
        row_html = f"""
            <tr>
                <td>{assignee}</td>
                <td>{count}</td>
            </tr>
        """
        html_content += row_html

    # Add the unassigned row
    row_html = f"""
        <tr>
            <td>Unassigned</td>
            <td>{unassigned_count}</td>
        </tr>
    """
    html_content += row_html

    # Close the HTML content for Assignee Summary table
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

import os
import requests
from requests.auth import HTTPBasicAuth
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
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

def send_email(sender_email, receiver_email, subject, body, attachments=[]):
    # Create a multipart message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Attach HTML content to email
    msg.attach(MIMEText(body, 'html'))

    # Attach files to the email
    for attachment_path in attachments:
        with open(attachment_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(attachment_path)}')
        msg.attach(part)

    # Log in to the SMTP server and send email
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, 'your_password')  # You should securely manage this password
        server.sendmail(sender_email, receiver_email, msg.as_string())

# Replace these with your Jira and email details
jira_url = "your_jira_url"
username = "your_username"
password = "your_password"
project_keys = ["project_key_1", "project_key_2", "project_key_3"]
sender_email = "your_email@gmail.com"
receiver_email = "recipient_email@gmail.com"
subject = "Open Issues Report"

# Define column widths
sl_width = 5
jira_number_width = 15
status_width = 20
assignee_width = 20
summary_width = 50
created_date_width = 20

# Create HTML content for each project and save to files
attachments = []
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

        # Sort issues by age in descending order
        open_issues.sort(
            key=lambda issue: (datetime.now(timezone.utc) - datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z")).days, 
            reverse=True
        )

        # Initialize HTML content for the project key
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                }}
                .header {{
                    background-color: #A533FF;
                    color: white;
                    padding: 10px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 20px;
                }}
                th {{
                    border: 1px solid black;
                    padding: 8px;
                    text-align: center;
                    background-color: #A533FF;
                    color: white;
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
                .green {{
                    background-color: limegreen;
                }}
                .orange {{
                    background-color: orange;
                }}
                .red {{
                    background-color: red;
                }}
            </style>
        </head>
        <body>
            <h2 class='header'>Jira Open Issues for {project_key}</h2>
            <table>
                <tr>
                    <th>SL. No</th>
                    <th>Jira Number</th>
                    <th>Status</th>
                    <th>Assignee</th>
                    <th>Summary</th>
                    <th>Created Date</th>
                    <th>Age of Ticket</th>
                </tr>
        """

        # Add rows to HTML content with clickable links
        for index, issue in enumerate(open_issues, start=1):
            jira_number = issue['key'][:jira_number_width]
            status = issue['fields']['status']['name'][:status_width]
            assignee = (issue['fields']['assignee']['displayName'] if 'assignee' in issue['fields'] and issue['fields']['assignee'] else 'Unassigned')[:assignee_width]
            summary = issue['fields']['summary'][:summary_width]
            created_date = datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%d")
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

        # Close the HTML content for the open issues table
        html_content += """
            </table>
        """

        # Add Issue Summary table
        html_content += f"""
        <table>
            <tr>
                <th colspan="2" class="header">Issue Summary</th>
            </tr>
            <tr>
                <td>Category</td>
                <td>Total</td>
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
        html_content += f"""
        <table>
            <tr>
                <th colspan="2" class="header">Assignee Summary</th>
            </tr>
            <tr>
                <td>Assignee</td>
                <td>Total</td>
            </tr>
        """

        # Add assignee rows
        for assignee, count in sorted_assignees:
            html_content += f"""
            <tr>
                <td>{assignee}</td>
                <td>{count}</td>
            </tr>
            """

        html_content += f"""
            <tr>
                <td>Unassigned</td>
                <td>{unassigned_count}</td>
            </tr>
        </table>
        </body>
        </html>
        """

        # Save the HTML content to a file
        html_filename = f'open_issues_{project_key}.html'
        with open(html_filename, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content)

        attachments.append(html_filename)
        print(f"HTML file '{html_filename}' created successfully.")

# Create email body with instructions to open attachments
email_body = """
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
        }
    </style>
</head>
<body>
    <p>Hi Team,</p>
    <p>Please find attached the open issues for the respective projects:</p>
    <ul>
"""

# Add instructions to open attachments in the email body
for project_key in project_keys:
    email_body += f'<li><a href="cid:open_issues_{project_key}.html">Open Issues for {project_key}</a></li>'

email_body += """
    </ul>
    <p>NOTE: This is an automated email. In case of any concerns please reach out to us at <a href="mailto:abc@gmail.com">abc@gmail.com</a>.</p>
    <p>Please download and open the attached HTML files to view the details.</p>
</body>
</html>
"""

# Send email with HTML content and attachments
send_email(sender_email, receiver_email, subject, email_body, attachments)

import os
import requests
from requests.auth import HTTPBasicAuth
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from email.mime.base import MIMEBase
from datetime import datetime, timezone

def get_open_issues(jira_url, username, password, project_key):
    response = requests.get(f"{jira_url}/rest/api/2/search?jql=project={project_key} AND status in (Open, 'In Progress', Reopened)",
                            auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        return response.json()['issues']
    else:
        return []

def send_email(sender_email, sender_password, receiver_email, subject, body, attachment_path=None):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    if attachment_path:
        with open(attachment_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {attachment_path}')
        msg.attach(part)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())

jira_url = "your_jira_url"
username = "your_username"
password = "your_password"
project_key = "your_project_key"
sender_email = "your_email@gmail.com"
sender_password = "your_email_password"
receiver_email = "recipient_email@gmail.com"
subject = "Open Issues Report"

sl_width = 5
jira_number_width = 15
status_width = 20
assignee_width = 20
summary_width = 50
created_date_width = 20
age_of_ticket_width = 15

html_filename = 'open_issues.html'
if os.path.exists(html_filename):
    os.remove(html_filename)
    print(f"Previous HTML file '{html_filename}' deleted.")

open_issues = get_open_issues(jira_url, username, password, project_key)

if open_issues:
    open_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'Open')
    in_progress_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'In Progress')
    reopened_count = sum(1 for issue in open_issues if issue['fields']['status']['name'] == 'Reopened')

    html_content = f"""
    <html>
    <head>
        <style>
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
            }}
            th, td {{
                border: 1px solid black;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background-color: #33FFBE;
                font-weight: bold;
                border: 1px solid #000;
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
            }}
        </style>
    </head>
    <body>
        <h1 class="main-header">Jira Open Issues for {project_key}</h1>
        <table>
            <tr>
                <th>SL.No</th>
                <th>Jira Number</th>
                <th>Status</th>
                <th>Assignee</th>
                <th>Summary</th>
                <th>Created Date</th>
                <th>Age of Ticket</th>
            </tr>
    """

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

    html_content += f"""
        </table>
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

    for assignee, count in sorted_assignees:
        row_html = f"""
            <tr>
                <td>{assignee}</td>
                <td>{count}</td>
            </tr>
        """
        html_content += row_html

    row_html = f"""
            <tr>
                <td>Unassigned</td>
                <td>{unassigned_count}</td>
            </tr>
    """
    html_content += row_html

    html_content += """
        </table>
    </body>
    </html>
    """

    with open(html_filename, 'w', encoding='utf-8') as html_file:
        html_file.write(html_content)

    print(f"HTML file '{html_filename}' created successfully.")

    send_email(sender_email, sender_password, receiver_email, subject, html_content)
else:
    print("Failed to retrieve open issues.")

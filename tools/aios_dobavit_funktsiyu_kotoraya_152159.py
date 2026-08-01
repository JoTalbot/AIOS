import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dataclasses import dataclass
from typing import List

@dataclass
class TodoReport:
    """Data class to hold TODO/FIXME/HACK report"""
    path: str
    comments: List[str]

def scan_code_for_comments(path: str) -> List[TodoReport]:
    """Scan code for TODO/FIXME/HACK comments and generate report"""
    try:
        with open(path, 'r') as file:
            content = file.read()
            comments = re.findall(r'#\s*(TODO|FIXME|HACK): (.*)', content)
            return [
                TodoReport(path, [comment[1]])
                for comment in comments
            ]
    except FileNotFoundError:
        print(f"File {path} not found")
        return []
    except Exception as e:
        print(f"Error scanning file {path}: {e}")
        return []

def send_email(subject: str, body: str, from_addr: str, to_addr: str, password: str) -> None:
    """Send email with given subject and body"""
    try:
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_addr, password)
        text = msg.as_string()
        server.sendmail(from_addr, to_addr, text)
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

def generate_report(comments: List[TodoReport]) -> str:
    """Generate report from comments"""
    report = "TODO/FIXME/HACK Report:\n"
    for comment in comments:
        report += f"- {comment.path}:\n  - {comment.comments[0]}\n"
    return report

def main() -> None:
    """Main function to test the module"""
    target_path = 'tools/aios_dobavit_funktsiyu_kotoraya_152159.py'
    comments = scan_code_for_comments(target_path)
    report = generate_report(comments)
    if comments:
        subject = "TODO/FIXME/HACK Report"
        body = report
        from_addr = "your-email@gmail.com"
        to_addr = "recipient-email@gmail.com"
        password = "your-password"
        send_email(subject, body, from_addr, to_addr, password)
        print(report)
    else:
        print("No TODO/FIXME/HACK comments found")

if __name__ == '__main__':
    main()

__all__ = ['scan_code_for_comments', 'send_email', 'generate_report']
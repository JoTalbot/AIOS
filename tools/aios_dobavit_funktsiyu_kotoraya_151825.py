import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dataclasses import dataclass
from typing import List

@dataclass
class TodoItem:
    """Data class to represent a TODO/FIXME/HACK item."""
    file_path: str
    line_number: int
    text: str

class TodoScanner:
    """Class to scan project code for TODO/FIXME/HACK comments."""
    def __init__(self, target_path: str):
        self.target_path = target_path

    def scan(self) -> List[TodoItem]:
        """Scan code in target path for TODO/FIXME/HACK comments."""
        todo_items = []
        for root, dirs, files in os.walk(self.target_path):
            for file in files:
                if file.endswith(('.py', '.txt')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        for line_number, line in enumerate(f, start=1):
                            if re.search(r'\b(TODO|FIXME|HACK)\b', line, re.IGNORECASE):
                                match = re.search(r'\b(TODO|FIXME|HACK)\b', line, re.IGNORECASE)
                                todo_items.append(TodoItem(file_path, line_number, match.group()))
        return todo_items

class EmailSender:
    """Class to send email with TODO/FIXME/HACK report."""
    def __init__(self, sender_email: str, sender_password: str, recipient_email: str):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send_email(self, subject: str, body: str):
        """Send email with TODO/FIXME/HACK report."""
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(self.sender_email, self.sender_password)
        text = msg.as_string()
        server.sendmail(self.sender_email, self.recipient_email, text)
        server.quit()

def generate_report(todo_items: List[TodoItem]) -> str:
    """Generate TODO/FIXME/HACK report."""
    report = "TODO/FIXME/HACK Report:\n"
    for item in todo_items:
        report += f"File: {item.file_path}, Line: {item.line_number}, Text: {item.text}\n"
    return report

def main():
    """Main function to test TodoScanner and EmailSender."""
    scanner = TodoScanner('tools')
    todo_items = scanner.scan()
    if todo_items:
        sender = EmailSender('your_email@gmail.com', 'your_password', 'recipient_email@example.com')
        report = generate_report(todo_items)
        sender.send_email('TODO/FIXME/HACK Report', report)
        print("Email sent successfully!")
    else:
        print("No TODO/FIXME/HACK comments found.")

if __name__ == '__main__':
    main()
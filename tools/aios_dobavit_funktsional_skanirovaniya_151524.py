import pylint.lint
from pylint.reporters.text import TextReporter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import re
import logging
from logging.handlers import RotatingFileHandler
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('technical_debt.log', maxBytes=1000000, backupCount=1),
        logging.StreamHandler()
    ]
)

class TechnicalDebtReporter(TextReporter):
    """Custom reporter for pylint to generate technical debt report."""
    
    def __init__(self, output):
        super().__init__(output)
        self.technical_debt = []
        self.tags = ['TODO', 'FIXME', 'HACK']

    def handle_message(self, msg):
        """Handle message from pylint."""
        if msg.msg_id in self.tags:
            self.technical_debt.append(msg)

    def display_results(self):
        """Display technical debt report."""
        if self.technical_debt:
            logging.info('Technical Debt Report:')
            for msg in self.technical_debt:
                logging.info(f'File: {msg.path}, Line: {msg.line}, Message: {msg.msg}')
        else:
            logging.info('No technical debt found.')

def scan_code(path: str) -> list:
    """Scan code for technical debt."""
    try:
        pylint.lint.Run(['--load-plugins=pylint.extensions.pylint', path], reporter=TechnicalDebtReporter('report.txt'))
        with open('report.txt', 'r') as f:
            report = f.readlines()
        technical_debt = []
        for line in report:
            if any(tag in line for tag in ['TODO', 'FIXME', 'HACK']):
                technical_debt.append(line.strip())
        return technical_debt
    except Exception as e:
        logging.error(f'Error scanning code: {e}')
        return []

def send_report(technical_debt: list, email: str, password: str, recipient: str) -> None:
    """Send technical debt report via email."""
    try:
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = recipient
        msg['Subject'] = 'Technical Debt Report'
        body = '\n'.join(technical_debt)
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email, password)
        text = msg.as_string()
        server.sendmail(email, recipient, text)
        server.quit()
        logging.info('Report sent via email.')
    except Exception as e:
        logging.error(f'Error sending report via email: {e}')

def send_report_telegram(technical_debt: list, token: str, chat_id: str) -> None:
    """Send technical debt report via Telegram."""
    try:
        bot = Bot(token)
        bot.send_message(chat_id=chat_id, text='\n'.join(technical_debt))
        logging.info('Report sent via Telegram.')
    except Exception as e:
        logging.error(f'Error sending report via Telegram: {e}')

def main() -> None:
    """Main function."""
    path = input('Enter path to scan: ')
    technical_debt = scan_code(path)
    if technical_debt:
        send_report(technical_debt, 'your_email@gmail.com', 'your_password', 'recipient_email@example.com')
        send_report_telegram(technical_debt, 'your_telegram_token', 'your_chat_id')
    else:
        logging.info('No technical debt found.')

if __name__ == '__main__':
    main()

__all__ = ['scan_code', 'send_report', 'send_report_telegram']
"""Tests for run_telegram_bot.py"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
from run_telegram_bot import send_message, process_update, handle_command, handle_message, process_command

class TestRunTelegramBot(unittest.TestCase):
    """Tests for run_telegram_bot.py"""

    def setUp(self):
        """Setup before each test"""
        self.mock_bot = Mock()
        self.mock_update = Mock()
        self.mock_context = Mock()

    @patch('run_telegram_bot.bot')
    def test_send_message(self, mock_bot: 'Bot') -> None:
        """Test send_message function"""
        message = "Test message"
        send_message(self.mock_bot, message)
        mock_bot.send_message.assert_called_once_with(message)

    @patch('run_telegram_bot.bot')
    def test_process_update(self, mock_bot: 'Bot') -> None:
        """Test process_update function"""
        update = self.mock_update
        process_update(self.mock_bot, update)
        mock_bot.process_update.assert_called_once_with(update)

    @patch('run_telegram_bot.bot')
    def test_handle_command(self, mock_bot: 'Bot') -> None:
        """Test handle_command function"""
        command = "Test command"
        handle_command(self.mock_bot, command)
        mock_bot.handle_command.assert_called_once_with(command)

    @patch('run_telegram_bot.bot')
    def test_handle_message(self, mock_bot: 'Bot') -> None:
        """Test handle_message function"""
        message = "Test message"
        handle_message(self.mock_bot, message)
        mock_bot.handle_message.assert_called_once_with(message)

    @patch('run_telegram_bot.bot')
    def test_process_command(self, mock_bot: 'Bot') -> None:
        """Test process_command function"""
        command = "Test command"
        process_command(self.mock_bot, command)
        mock_bot.process_command.assert_called_once_with(command)

    def test_main(self):
        """Test main function"""
        with patch('sys.argv', ['run_telegram_bot.py', '--test']):
            with self.assertRaises(SystemExit):
                sys.modules['run_telegram_bot'].main()

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    __all__ = ['TestRunTelegramBot']
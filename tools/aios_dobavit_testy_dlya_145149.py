"""
Модуль для добавления тестов к функциям run_coder_orchestrator.py.
"""

import unittest
from unittest.mock import Mock, patch
from tools.aios_dobavit_testy_dlya_145149 import run_coder_orchestrator

class TestRunCoderOrchestrator(unittest.TestCase):
    """
    Класс для тестирования функций run_coder_orchestrator.py.
    """

    def setUp(self):
        """
        Метод для подготовки тестового окружения.
        """
        self.mock_bot = Mock()
        self.mock_llm_balancer = Mock()

    def test_run_coder_orchestrator_bot_response(self):
        """
        Тест функции run_coder_orchestrator с ответом бота.
        """
        # Arrange
        response = "Test bot response"
        self.mock_bot.get_response.return_value = response

        # Act
        result = run_coder_orchestrator.run_coder_orchestrator(self.mock_bot, self.mock_llm_balancer)

        # Assert
        self.assertEqual(result, response)

    def test_run_coder_orchestrator_llm_balancer_response(self):
        """
        Тест функции run_coder_orchestrator с ответом балансировщика LLM.
        """
        # Arrange
        response = "Test LLM balancer response"
        self.mock_llm_balancer.get_response.return_value = response

        # Act
        result = run_coder_orchestrator.run_coder_orchestrator(self.mock_bot, self.mock_llm_balancer)

        # Assert
        self.assertEqual(result, response)

    def test_run_coder_orchestrator_both_responses(self):
        """
        Тест функции run_coder_orchestrator с ответами бота и балансировщика LLM.
        """
        # Arrange
        bot_response = "Test bot response"
        llm_balancer_response = "Test LLM balancer response"
        self.mock_bot.get_response.return_value = bot_response
        self.mock_llm_balancer.get_response.return_value = llm_balancer_response

        # Act
        result = run_coder_orchestrator.run_coder_orchestrator(self.mock_bot, self.mock_llm_balancer)

        # Assert
        self.assertEqual(result, bot_response)

    def test_run_coder_orchestrator_exception(self):
        """
        Тест функции run_coder_orchestrator с исключением.
        """
        # Arrange
        self.mock_bot.get_response.side_effect = Exception("Test exception")

        # Act and Assert
        with self.assertRaises(Exception):
            run_coder_orchestrator.run_coder_orchestrator(self.mock_bot, self.mock_llm_balancer)

if __name__ == '__main__':
    unittest.main()
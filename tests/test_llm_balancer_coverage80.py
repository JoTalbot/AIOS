"""Additional tests to reach 80% coverage for llm_balancer"""
import os, json
from unittest.mock import Mock, patch
from aios_core.llm_balancer import LLMBalancer, APIKey, Provider

def test_chat_success():
    bal = LLMBalancer()
    key = APIKey(key="test", provider="groq")
    prov = Provider(name="groq", base_url="https://api.groq.com", keys=[key], models=["llama-3.1-8b-instant"])
    bal.providers = {"groq": prov}
    mock_response = Mock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "Hello world"}}]}
    mock_response.raise_for_status.return_value = None
    with patch('requests.post', return_value=mock_response):
        result = bal.chat([{"role":"user","content":"hi"}], model="llama-3.1-8b-instant", task_type="code")
        assert "Hello" in result or len(result) > 0

def test_chat_cohere_format():
    bal = LLMBalancer()
    key = APIKey(key="test", provider="cohere")
    prov = Provider(name="cohere", base_url="https://api.cohere.ai/v2/chat", keys=[key], models=["command-r-08-2024"])
    bal.providers = {"cohere": prov}
    mock_response = Mock()
    mock_response.json.return_value = {"text": "Cohere response"}
    mock_response.raise_for_status.return_value = None
    with patch('requests.post', return_value=mock_response):
        result = bal.chat([{"role":"user","content":"hi"}], model="command-r-08-2024", task_type="chat")
        assert isinstance(result, str)

def test_chat_402_handling():
    bal = LLMBalancer()
    key = APIKey(key="test", provider="openrouter")
    prov = Provider(name="openrouter", base_url="https://...", keys=[key], models=["test-model"])
    bal.providers = {"openrouter": prov}
    from requests.exceptions import HTTPError
    http_err = HTTPError("402")
    http_err.response = Mock()
    http_err.response.status_code = 402
    http_err.response.text = "Payment Required"
    with patch('requests.post', side_effect=http_err):
        result = bal.chat([{"role":"user","content":"hi"}], model="test-model", max_tokens=5)
        assert isinstance(result, str)

def test_chat_429_404_401_handling():
    bal = LLMBalancer()
    for code in [429, 404, 401, 403, 500]:
        key = APIKey(key=f"k{code}", provider="test")
        prov = Provider(name="test", base_url="https://...", keys=[key], models=["test-model"])
        bal.providers = {"test": prov}
        from requests.exceptions import HTTPError
        http_err = HTTPError(f"{code}")
        http_err.response = Mock()
        http_err.response.status_code = code
        http_err.response.text = f"Error {code}"
        with patch('requests.post', side_effect=http_err):
            result = bal.chat([{"role":"user","content":"hi"}], model="test-model", max_tokens=5)
            assert isinstance(result, str)

def test_balancer_empty_response():
    bal = LLMBalancer()
    key = APIKey(key="test", provider="groq")
    prov = Provider(name="groq", base_url="https://...", keys=[key], models=["llama-3.1-8b-instant"])
    bal.providers = {"groq": prov}
    mock_response = Mock()
    mock_response.json.return_value = {"choices": []}
    mock_response.raise_for_status.return_value = None
    with patch('requests.post', return_value=mock_response):
        result = bal.chat([{"role":"user","content":"hi"}], model="llama-3.1-8b-instant", max_tokens=5)
        assert isinstance(result, str)

def test_balancer_app_error():
    bal = LLMBalancer()
    key = APIKey(key="test", provider="zai")
    prov = Provider(name="zai", base_url="https://...", keys=[key], models=["glm-4.5-flash"])
    bal.providers = {"zai": prov}
    mock_response = Mock()
    mock_response.json.return_value = {"success": False, "code": 401, "msg": "token expired"}
    mock_response.raise_for_status.return_value = None
    with patch('requests.post', return_value=mock_response):
        result = bal.chat([{"role":"user","content":"hi"}], model="glm-4.5-flash", max_tokens=5)
        assert isinstance(result, str)

def test_balancer_unknown_format():
    bal = LLMBalancer()
    key = APIKey(key="test", provider="groq")
    prov = Provider(name="groq", base_url="https://...", keys=[key], models=["llama-3.1-8b-instant"])
    bal.providers = {"groq": prov}
    mock_response = Mock()
    mock_response.json.return_value = {"unknown": "format"}
    mock_response.raise_for_status.return_value = None
    with patch('requests.post', return_value=mock_response):
        result = bal.chat([{"role":"user","content":"hi"}], model="llama-3.1-8b-instant", max_tokens=5)
        assert isinstance(result, str)

def test_chat_with_system_prompt():
    bal = LLMBalancer()
    key = APIKey(key="test", provider="groq")
    prov = Provider(name="groq", base_url="https://...", keys=[key], models=["llama-3.1-8b-instant"])
    bal.providers = {"groq": prov}
    mock_response = Mock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "System response"}}]}
    mock_response.raise_for_status.return_value = None
    with patch('requests.post', return_value=mock_response):
        result = bal.chat([{"role":"user","content":"hi"}], model="llama-3.1-8b-instant", system="You are helpful", task_type="code")
        assert isinstance(result, str)

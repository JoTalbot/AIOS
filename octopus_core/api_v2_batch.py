import json
import requests
from typing import Dict, Any

def replace_get_with_post(api_url: str, token: str, command: str) -> Dict[str, Any]:
    """
    Replaces GET requests with POST requests for Gemini commands,
    sending data in the request body as JSON.

    Args:
        api_url: The base URL for the API.
        token: The authentication token.
        command: The command to be executed.

    Returns:
        The JSON response from the API.
    """
    headers = {"Content-Type": "application/json"}
    data = {"token": token, "command": command}
    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during API call: {e}")
        return {}  # Or raise the exception, depending on desired behavior

# Example Usage (replace with actual API endpoint)
# api_url = "https://your-api-endpoint.com/gemini"
# token = "your_auth_token"
# command = "your_gemini_command"
# result = replace_get_with_post(api_url, token, command)
# print(result)
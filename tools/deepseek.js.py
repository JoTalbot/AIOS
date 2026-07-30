"""
Deepseek API client with credit usage monitoring and alternative provider switching.

This module provides a client for interacting with the Deepseek API, monitoring credit usage, and switching to alternative providers when the credit limit is reached.
"""

import requests
from dataclasses import dataclass
from typing import Dict, List

__all__ = ['DeepseekClient', 'AlternativeProvider']

@dataclass
class AlternativeProvider:
    """Alternative provider configuration."""
    name: str
    api_url: str
    api_key: str

class DeepseekClient:
    """Deepseek API client with credit usage monitoring and alternative provider switching."""

    def __init__(self, api_key: str, credit_limit: int, alternative_providers: List[AlternativeProvider]):
        """
        Initialize the Deepseek client.

        Args:
        - api_key (str): Deepseek API key.
        - credit_limit (int): Credit limit for the Deepseek API.
        - alternative_providers (List[AlternativeProvider]): List of alternative providers to switch to when the credit limit is reached.
        """
        self.api_key = api_key
        self.credit_limit = credit_limit
        self.alternative_providers = alternative_providers
        self.current_provider_index = 0
        self.credit_usage = 0

    def _get_current_provider(self) -> AlternativeProvider:
        """Get the current alternative provider."""
        if self.current_provider_index >= len(self.alternative_providers):
            self.current_provider_index = 0
        return self.alternative_providers[self.current_provider_index]

    def _switch_to_next_provider(self) -> None:
        """Switch to the next alternative provider."""
        self.current_provider_index += 1

    def _check_credit_usage(self) -> bool:
        """Check if the credit usage has reached the limit."""
        return self.credit_usage >= self.credit_limit

    def make_request(self, endpoint: str, params: Dict[str, str]) -> requests.Response:
        """
        Make a request to the Deepseek API or the current alternative provider.

        Args:
        - endpoint (str): API endpoint.
        - params (Dict[str, str]): Request parameters.

        Returns:
        - requests.Response: API response.
        """
        if self._check_credit_usage():
            self._switch_to_next_provider()
            provider = self._get_current_provider()
            url = f"{provider.api_url}{endpoint}"
            headers = {'Authorization': f"Bearer {provider.api_key}"}
        else:
            url = f"https://api.deepseek.com/{endpoint}"
            headers = {'Authorization': f"Bearer {self.api_key}"}

        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            self.credit_usage += 1  # increment credit usage for successful requests
        return response

if __name__ == '__main__':
    # Example usage
    alternative_providers = [
        AlternativeProvider('llama-4-maverick', 'https://api.llama-4-maverick.com/', 'alternative_api_key'),
    ]
    client = DeepseekClient('deepseek_api_key', 100, alternative_providers)

    response = client.make_request('example/endpoint', {'param1': 'value1'})
    print(response.json())
from typing import Dict, Any
import urllib.parse

def replace_hack_get_request(url: str, token: str) -> str:
    """
    Replaces a potentially unsafe GET request with a secure method using a token in the URL.

    Args:
        url (str): The base URL for the GET request.
        token (str): The authentication token.

    Returns:
        str: The modified URL with the token included.
    """
    # Encode the token to be URL-safe
    encoded_token = urllib.parse.quote(token)

    # Construct the new URL with the token
    new_url = f"{url}?token={encoded_token}"

    return new_url

# Example usage (replace with actual URL and token)
# url = "https://example.com/instructions"
# token = "your_secret_token"
# secure_url = replace_hack_get_request(url, token)
# print(secure_url)
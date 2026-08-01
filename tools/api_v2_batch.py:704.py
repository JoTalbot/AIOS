import requests
from dataclasses import dataclass

@dataclass
class ApiRequest:
    url: str
    token: str

def fetch_data(api_request):
    try:
        response = requests.get(api_request.url, headers={'Authorization': f'Token {api_request.token}'})
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def main():
    api_request = ApiRequest(url="https://example.com/api/data", token="your_token_here")
    data = fetch_data(api_request)
    if data is not None:
        print(data)

if __name__ == '__main__':
    main()
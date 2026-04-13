import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. Paste your authorization code from the URL here
AUTHORIZATION_CODE = "ba44fa8641d3f4866c94a9bcae13769d612b4cc0"

def exchange_token(auth_code: str) -> None:
    """Exchanges the temporary authorization code for a permanent refresh token."""
    print("Initiating token exchange with Strava API...")

    client_id = os.getenv('STRAVA_CLIENT_ID')
    client_secret = os.getenv('STRAVA_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("Error: Missing Client ID or Client Secret in .env file.")
        return

    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': auth_code,
        'grant_type': 'authorization_code'
    }

    try:
        response = requests.post("https://www.strava.com/oauth/token", data=payload)
        response.raise_for_status()

        data = response.json()
        refresh_token = data.get('refresh_token')

        print("\nToken exchange successful.")
        print("Your new Refresh Token is:")
        print("-" * 50)
        print(refresh_token)
        print("-" * 50)
        print("Action required: Update STRAVA_REFRESH_TOKEN in your .env file with this value.")

    except requests.exceptions.RequestException as e:
        print(f"Error during token exchange: {e}")
        try:
            print(f"API Response: {response.json()}")
        except ValueError:
            print("Could not parse API response as JSON.")


if __name__ == "__main__":
    exchange_token(AUTHORIZATION_CODE)
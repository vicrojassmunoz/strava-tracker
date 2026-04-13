import requests
import os
from dotenv import load_dotenv

load_dotenv()


class StravaClient:
    def __init__(self):
        self.client_id = os.getenv('STRAVA_CLIENT_ID')
        self.client_secret = os.getenv('STRAVA_CLIENT_SECRET')
        self.refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
        self.base_url = "https://www.strava.com/api/v3"
        self.access_token = None

    def _refresh_access_token(self) -> str:
        """Exchanges the refresh token for a new short-lived access token."""
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        response = requests.post("https://www.strava.com/oauth/token", data=payload)
        response.raise_for_status()
        return response.json().get('access_token')

    def get_activities(self, limit: int = 1) -> list:
        """Fetches the latest activities from the athlete's profile."""
        if not self.access_token:
            self.access_token = self._refresh_access_token()

        headers = {'Authorization': f'Bearer {self.access_token}'}
        params = {'per_page': limit}

        response = requests.get(f"{self.base_url}/athlete/activities", headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_activity_details(self, activity_id: int) -> dict:
        """Fetches the FULL detailed JSON of a specific activity."""
        if not self.access_token:
            self.access_token = self._refresh_access_token()

        headers = {'Authorization': f'Bearer {self.access_token}'}

        # Notice we hit /activities/{id} instead of /athlete/activities
        response = requests.get(f"{self.base_url}/activities/{activity_id}", headers=headers)
        response.raise_for_status()
        return response.json()
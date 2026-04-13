import os
import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class StravaClient:
    BASE_URL = "https://www.strava.com/api/v3"
    TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self):
        self.client_id = os.getenv('STRAVA_CLIENT_ID')
        self.client_secret = os.getenv('STRAVA_CLIENT_SECRET')
        self.refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
        self.access_token = None

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError("Missing Strava credentials in .env (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)")

        logger.debug("StravaClient initialized")

    def _refresh_access_token(self) -> str:
        logger.debug("Refreshing Strava access token...")
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        response = requests.post(self.TOKEN_URL, data=payload, timeout=10)
        response.raise_for_status()
        token = response.json().get('access_token')
        logger.success("Access token refreshed")
        return token

    def _get_headers(self) -> dict:
        if not self.access_token:
            self.access_token = self._refresh_access_token()
        return {'Authorization': f'Bearer {self.access_token}'}

    def get_activities(self, limit: int = 1) -> list:
        logger.info(f"Fetching last {limit} activit{'y' if limit == 1 else 'ies'} from Strava...")
        response = requests.get(
            f"{self.BASE_URL}/athlete/activities",
            headers=self._get_headers(),
            params={'per_page': limit},
            timeout=10
        )
        response.raise_for_status()
        activities = response.json()
        logger.debug(f"  Retrieved {len(activities)} activit{'y' if len(activities) == 1 else 'ies'}")
        return activities

    def get_activity_details(self, activity_id: int) -> dict:
        logger.info(f"Fetching full detail for activity {activity_id}...")
        response = requests.get(
            f"{self.BASE_URL}/activities/{activity_id}",
            headers=self._get_headers(),
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        logger.debug(f"  Fields received: {len(data)}")
        logger.success(f"Activity detail fetched: '{data.get('name', 'Unknown')}'")
        return data
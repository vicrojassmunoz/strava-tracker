import json
import os
import time
import requests
from loguru import logger
from dotenv import load_dotenv
from fitness_client import FitnessClient
from config import RAILWAY_GRAPHQL_URL

load_dotenv()

TOKENS_FILE = ".tokens.json"

RAILWAY_UPSERT_MUTATION = """
mutation variableUpsert($input: VariableUpsertInput!) {
  variableUpsert(input: $input)
}
"""


class StravaClient(FitnessClient):
    BASE_URL = "https://www.strava.com/api/v3"
    TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self):
        self.client_id = os.getenv('STRAVA_CLIENT_ID')
        self.client_secret = os.getenv('STRAVA_CLIENT_SECRET')
        self.refresh_token = self._load_refresh_token()
        self.access_token = None
        self._token_expires_at = 0  # unix timestamp; 0 forces immediate refresh

        self._railway_api_token = os.getenv('RAILWAY_API_TOKEN')
        self._railway_service_id = os.getenv('RAILWAY_SERVICE_ID')
        self._railway_environment_id = os.getenv('RAILWAY_ENVIRONMENT_ID')
        self._railway_project_id = os.getenv('RAILWAY_PROJECT_ID')

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError("Missing Strava credentials in .env (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)")

        logger.debug("StravaClient initialized")

    def _load_refresh_token(self) -> str | None:
        try:
            with open(TOKENS_FILE) as f:
                token = json.load(f).get("refresh_token")
                if token:
                    logger.debug(f"Loaded refresh token from {TOKENS_FILE}")
                    return token
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning(f"Could not read {TOKENS_FILE}: {exc}")
        return os.getenv('STRAVA_REFRESH_TOKEN')

    def _save_refresh_token(self, token: str) -> None:
        try:
            with open(TOKENS_FILE, "w") as f:
                json.dump({"refresh_token": token}, f)
            logger.debug(f"Saved refresh token to {TOKENS_FILE}")
        except Exception as exc:
            logger.warning(f"Could not write {TOKENS_FILE}: {exc}")

    def _rotate_railway_refresh_token(self, new_token: str) -> None:
        required = {
            'RAILWAY_API_TOKEN': self._railway_api_token,
            'RAILWAY_SERVICE_ID': self._railway_service_id,
            'RAILWAY_ENVIRONMENT_ID': self._railway_environment_id,
            'RAILWAY_PROJECT_ID': self._railway_project_id,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            logger.warning(f"Skipping Railway token rotation — missing env vars: {', '.join(missing)}")
            return

        payload = {
            "query": RAILWAY_UPSERT_MUTATION,
            "variables": {
                "input": {
                    "projectId": self._railway_project_id,
                    "serviceId": self._railway_service_id,
                    "environmentId": self._railway_environment_id,
                    "name": "STRAVA_REFRESH_TOKEN",
                    "value": new_token,
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self._railway_api_token}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(RAILWAY_GRAPHQL_URL, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            if result.get("errors"):
                logger.error(f"Railway API error during token rotation: {result['errors']}")
            else:
                logger.success("STRAVA_REFRESH_TOKEN rotated and saved to Railway")
        except Exception as exc:
            logger.error(f"Failed to update STRAVA_REFRESH_TOKEN in Railway: {exc}")

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
        data = response.json()
        token = data.get('access_token')
        self._token_expires_at = data.get('expires_at', 0)

        new_refresh_token = data.get('refresh_token')
        if new_refresh_token and new_refresh_token != self.refresh_token:
            logger.info("Strava issued a new refresh_token — rotating...")
            self.refresh_token = new_refresh_token
            self._save_refresh_token(new_refresh_token)
            self._rotate_railway_refresh_token(new_refresh_token)

        logger.success("Access token refreshed")
        return token

    def _get_headers(self) -> dict:
        if not self.access_token or time.time() >= self._token_expires_at - 60:
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
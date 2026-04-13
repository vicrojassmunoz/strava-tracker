import os
import requests
from dotenv import load_dotenv

# Load secrets
load_dotenv()

CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.getenv('STRAVA_REFRESH_TOKEN')


def get_strava_data():
    print("Requesting permissions from strava")

    # Get access token
    auth_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token',
        'f': 'json'
    }

    auth_response = requests.post(auth_url, data=payload)

    # Check keys
    if auth_response.status_code != 200:
        print("Error reading credentials")
        print(auth_response.json())
        return

    # Save access token
    access_token = auth_response.json().get('access_token')
    print("Successful login")

    # Check last activity
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'per_page': 1}

    act_response = requests.get(activities_url, headers=headers, params=params)

    if act_response.status_code == 200:
        activities = act_response.json()
        if activities:
            latest = activities[0]

            # Clean data
            nombre = latest.get('name')
            distancia = latest.get('distance') / 1000

            print("Connection success. Last activity:")
            print(f"Title: {nombre}")
            print(f"Distance: {distancia:.2f} km")
        else:
            print("You have no activities")
    else:
        print("Error getting activities")
        print(act_response.json())

if __name__ == '__main__':
    get_strava_data()
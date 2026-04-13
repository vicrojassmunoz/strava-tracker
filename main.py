import os
import json
from datetime import datetime

from strava_client import StravaClient


def main():
    print("Initializing application...")

    try:
        client = StravaClient()
        print("Successfully connected. Fetching latest activity ID...")

        # 1. Get the summary to find the ID of your last run
        activities = client.get_activities(limit=1)

        if activities:
            activity_id = activities[0].get('id')
            print(f"Target locked. Activity ID: {activity_id}")
            print("Downloading FULL detailed data. This might be massive...")

            # 2. Get the full details using the ID
            detailed_data = client.get_activity_details(activity_id)

            # Create a timestamp (e.g., 20240523_101530)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"activity_{timestamp}.json"
            filepath = os.path.join("data", filename)

            # Ensure the 'data' directory exists
            os.makedirs("data", exist_ok=True)

            # 3. Save it all to a file to inspect it comfortably
            print(f"Saving detailed report to {filepath}...")
            with open(filepath, "w", encoding="utf-8") as file:
                json.dump(detailed_data, file, indent=4)

            print("Data archived successfully.")

        else:
            print("No recent activities found.")

    except Exception as e:
        print(f"Critical error during execution: {e}")


if __name__ == '__main__':
    main()
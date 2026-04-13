from strava_client import StravaClient
from data_processing import StravaDataProcessor


def main():
    print("Initializing application...")

    try:
        client = StravaClient()
        print("Successfully connected to Strava API. Fetching latest activity...")

        activities = client.get_activities(limit=1)

        if activities:
            latest_activity = activities[0]

            # Process the raw data
            processor = StravaDataProcessor()
            processed_data = processor.process_activity(latest_activity)

            print("\n--- Processed Activity Report ---")
            print(f"Name:     {processed_data['name']}")
            print(f"Type:     {processed_data['type']}")
            print(f"Distance: {processed_data['distance_km']} km")
            print(f"Time:     {processed_data['duration']}")
            print(f"Pace:     {processed_data['pace']}")
            print("---------------------------------")
            print("Data ready for notification integration.")
        else:
            print("No recent activities found on this account.")

    except Exception as e:
        print(f"Critical error during execution: {e}")


if __name__ == '__main__':
    main()
class StravaDataProcessor:
    @staticmethod
    def process_activity(raw_activity: dict) -> dict:
        """
        Processes raw Strava activity data into a human-readable format.
        Calculates distance in km, formats time to MM:SS, and computes pace.
        """
        if not raw_activity:
            return {}

        distance_m = raw_activity.get('distance', 0)
        time_s = raw_activity.get('moving_time', 0)

        # 1. Distance to Kilometers
        distance_km = distance_m / 1000.0

        # 2. Time to MM:SS format
        minutes, seconds = divmod(time_s, 60)
        formatted_time = f"{int(minutes):02d}:{int(seconds):02d}"

        # 3. Calculate Pace (min/km)
        if distance_km > 0:
            pace_seconds_per_km = time_s / distance_km
            pace_min, pace_sec = divmod(pace_seconds_per_km, 60)
            formatted_pace = f"{int(pace_min):02d}:{int(pace_sec):02d}/km"
        else:
            formatted_pace = "00:00/km"

        return {
            "name": raw_activity.get('name', 'Unknown Activity'),
            "type": raw_activity.get('type', 'Unknown Type'),
            "distance_km": round(distance_km, 2),
            "duration": formatted_time,
            "pace": formatted_pace
        }
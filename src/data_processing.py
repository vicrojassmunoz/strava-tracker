from loguru import logger


class StravaDataProcessor:
    @staticmethod
    def process_activity(raw_activity: dict) -> dict:
        if not raw_activity:
            logger.warning("process_activity received empty data")
            return {}

        distance_m = raw_activity.get('distance', 0)
        time_s = raw_activity.get('moving_time', 0)
        avg_speed = raw_activity.get('average_speed', 0)  # m/s
        avg_hr = raw_activity.get('average_heartrate')
        max_hr = raw_activity.get('max_heartrate')
        elevation = raw_activity.get('total_elevation_gain', 0)

        # Distance
        distance_km = distance_m / 1000.0

        # Time — HH:MM:SS si supera la hora
        hours, remainder = divmod(time_s, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            formatted_time = f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
        else:
            formatted_time = f"{int(minutes):02d}:{int(seconds):02d}"

        # Pace desde average_speed (m/s) → min/km
        if avg_speed > 0:
            pace_min_km = 1000 / (avg_speed * 60)
            pace_min, pace_sec = divmod(pace_min_km * 60, 60)
            formatted_pace = f"{int(pace_min)}:{int(pace_sec):02d} min/km"
        elif distance_km > 0:
            # fallback con moving_time si no hay speed
            pace_sec_per_km = time_s / distance_km
            pace_min, pace_sec = divmod(pace_sec_per_km, 60)
            formatted_pace = f"{int(pace_min)}:{int(pace_sec):02d} min/km"
        else:
            formatted_pace = "--:-- min/km"

        result = {
            "name": raw_activity.get('name', 'Unknown Activity'),
            "type": raw_activity.get('type', 'Unknown Type'),
            "date": raw_activity.get('start_date_local', '')[:10],
            "distance_km": round(distance_km, 2),
            "duration": formatted_time,
            "pace": formatted_pace,
            "elevation_m": round(elevation, 1),
        }

        if avg_hr:
            result["avg_heartrate"] = avg_hr
        if max_hr:
            result["max_heartrate"] = max_hr

        logger.debug(f"Processed activity: {result['name']} | {result['distance_km']} km | {result['pace']} | {result['duration']}")
        return result
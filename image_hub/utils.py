from datetime import datetime, timezone

def time_now():
    return datetime.now(timezone.utc)

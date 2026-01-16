from skyfield.api import load, wgs84, EarthSatellite, utc
from datetime import datetime, timedelta
import pytz
import requests

# =========================
# CONFIG
# =========================
LAT, LON, ELEV_M = 13.0827, 80.2707, 6
TIMEZONE = pytz.timezone("Asia/Kolkata")

MIN_ELEVATION = 10
EARLY_ALERT_MINUTES = 10

SATELLITES = {
    "ISS": 25544,
    "HUBBLE": 20580,
    "TIANGONG": 48274
}

# =========================
# SKYFIELD
# =========================
load.directory = "/data/skyfield"

ts = load.timescale()
observer = wgs84.latlon(LAT, LON, elevation_m=ELEV_M)

eph = load("de421.bsp")
earth = eph["earth"]
sun = eph["sun"]

def fetch_satellite(norad_id):
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE"
    lines = requests.get(url, timeout=10).text.strip().splitlines()
    return EarthSatellite(lines[1], lines[2], lines[0], ts)

def is_night(t):
    astrometric = (earth + observer).at(t).observe(sun)
    alt, _, _ = astrometric.apparent().altaz()
    return alt.degrees < -6

# =========================
# MAIN
# =========================
results = []

now = ts.now()
end = ts.from_datetime(datetime.now(utc) + timedelta(hours=24))

for name, norad in SATELLITES.items():
    try:
        sat = fetch_satellite(norad)
        times, events = sat.find_events(observer, now, end, altitude_degrees=MIN_ELEVATION)

        for i, (t_event, event) in enumerate(zip(times, events)):
            if event != 0:
                continue  # rise only

            rise_utc = t_event.utc_datetime()
            rise_local = rise_utc.astimezone(TIMEZONE)

            seconds_to_rise = (rise_local - datetime.now(TIMEZONE)).total_seconds()
            if not (0 < seconds_to_rise <= EARLY_ALERT_MINUTES * 60):
                continue

            if not is_night(t_event):
                continue

            if i + 2 >= len(times):
                continue

            t_set = times[i + 2]
            t_mid = t_event + (t_set - t_event) / 2

            alt, az, _ = (sat - observer).at(t_mid).altaz()

            pass_key = f"{name}-{rise_utc.isoformat()}"

            results.append({
                "pass_key": pass_key,
                "satellite": name,
                "rise_time": rise_local.strftime("%H:%M:%S"),
                "max_elevation": round(alt.degrees, 1),
                "direction": az.compass_point()
            })

    except Exception as e:
        continue

return results #inside n8n python task works fine
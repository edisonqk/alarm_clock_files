import json
import threading
import os

CONFIG_FILE = "/home/edison/alarm_clock_files/clock_files/config.json"

_config_lock = threading.RLock()

DEFAULT_CONFIG = {
    "mode": "idle",
    "brightness": 50,
    "hand_position": 0,
    "alarm_time": 420,
    "alarm_armed": False,
    "alarm_active": False,
    "alarm_start_min": None,
    "last_ring_min": None,
    "snooze_until": None,
    "alarm_disabled_date": None
}

def read_config():
    with _config_lock:
        # If file missing → create default
        if not os.path.exists(CONFIG_FILE):
            write_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

        # Read file safely
        try:
            with open(CONFIG_FILE, "r") as f:
                raw = f.read().strip()
                if raw == "" or raw is None:
                    # Empty file → heal it
                    write_config(DEFAULT_CONFIG)
                    return DEFAULT_CONFIG.copy()
                return json.loads(raw)
        except:
            # JSON error → reset to defaults
            write_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

def write_config(cfg):
    with _config_lock:
        # Atomic write: write temp file then replace
        tmp_file = CONFIG_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(cfg, f, indent=4)
        os.replace(tmp_file, CONFIG_FILE)

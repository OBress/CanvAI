# read ~/data/user_db/user_settings.csv and load user settings into the environment

import csv
from pathlib import Path
import os

user_settings_path = Path(__file__).parent.parent.parent / 'data' / 'user_db' / 'user_settings.csv'
with open(user_settings_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        for key, value in row.items():
            os.environ[key.upper()] = value

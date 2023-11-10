"""Configuration file for Last FM analysis."""
import os

from dotenv import load_dotenv
import pycountry as pyc

DATA_PATH = "data/"
RESULTS_PATH = "results/"

dir_path = os.getcwd()
file_name = "last_fm.env"

load_dotenv(dotenv_path=dir_path + "/" + file_name)

try:
    LAST_FM_API_KEY = os.getenv("Key")
    LAST_FM_API_SECRET = os.getenv("Secret")
    LAST_FM_USERNAME = os.getenv("User")
except KeyError as e:
    raise RuntimeError("No last_fm_api_key or secret in environment") from e

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

LAST_FM_API_ROOT = "https://ws.audioscrobbler.com/2.0/"

COUNTRIES = [x.name for x in list(pyc.countries)]

COUNTRY_NAME_CHANGES = {"Czechia": "Czech Republic"}

COUNTRY_NAME_MAPPING = {
    "United States of America": "United States",
    "Russia": "Russian Federation",
    "Iran": "Iran, Islamic Republic of",
    "Dem. Rep. Congo": "Congo, The Democratic Republic of the",
    "Vietnam": "Viet Nam",
    "Laos": "Lao People's Democratic Republic",
    "Tanzania": "Tanzania, United Republic of",
    "South Korea": "Korea, Republic of",
    "Syria": "Syrian Arab Republic",
    "Czechia": "Czech Republic",
    "Solomon Is.": "Solomon Islands",
}

import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
class Configuration:

    class Google:
        CLIENT_ID = ""
        CLIENT_SECRET = ""

    
    class STRIPE_API:
        KEY = ""

    class ResourceValues:
        user_description_api = ""
        approach_api_description = ""
        approach_default_val = ""
        context_tooltip = ""

    class DefaultValues:
        config_file_path =  BASE_DIR/ "app/data/config-1.ini"
        database_path = BASE_DIR / "db.sqlite3"

    class Environment:
        DEVELOPMENT = "development"
        PRODUCTION = "production"
        TESTING = "testing"
        STAGING = "staging"
        LOCAL = "local"
        APP_URL = os.environ.get("APP_URL", "http://localhost:8000")
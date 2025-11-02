from datetime import timedelta
import os

DATABASE_URL = "auth-db" if ( "PRODUCTION" in os.environ ) else "localhost"

class Configuration:
    SQLALCHEMY_DATABASE_URI   = os.getenv("DATABASE_URI", f"mysql+pymysql://root:root@{DATABASE_URL}/auth_db")
    JWT_SECRET_KEY            = os.getenv("JWT_SECRET", "JWT_SECRET_DEV_KEY")
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta (hours=1)

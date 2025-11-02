import os

DATABASE_URL = "shop-db" if ( "PRODUCTION" in os.environ ) else "localhost"

class Configuration:
    SQLALCHEMY_DATABASE_URI   = os.getenv("DATABASE_URI", f"mysql+pymysql://root:root@{DATABASE_URL}/shop_db")
    JWT_SECRET_KEY            = os.getenv("JWT_SECRET", "JWT_SECRET_DEV_KEY")
    SOLC_VERSION = os.getenv("SOLC_VERSION", "0.8.18")
    WEB3_RPC = os.getenv("WEB3_RPC", "http://ganache:8454")
    OWNER_ADDRESS_INDEX = int(os.getenv("OWNER_ADDRESS_INDEX", "1"))
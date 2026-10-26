
import oracledb
from config import (
    DB_USER,
    DB_PASSWORD,
    DB_HOST,
    DB_PORT,
    DB_SERVICE
)


def get_connection():
    if not DB_USER or not DB_PASSWORD:
        raise ValueError("Database credentials are missing")

    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        service_name=DB_SERVICE
    )

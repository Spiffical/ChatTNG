from psycopg import connect
from psycopg.errors import OperationalError
from api.database import get_db_url
import logging

logger = logging.getLogger(__name__)

def check_database_connection() -> bool:
    """Check if the database is accessible."""
    try:
        # Get the sync URL for health checks
        _, db_url = get_db_url()
        
        # Try to connect using psycopg
        with connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
    except OperationalError as e:
        logger.error(f"Database health check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database health check: {e}")
        return False 
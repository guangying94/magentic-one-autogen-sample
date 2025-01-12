import os
import psycopg
import json
from dotenv import load_dotenv

load_dotenv()

POSTGRESQL_HOST=os.getenv('POSTGRESQL_HOST')
POSTGRESQL_DB=os.getenv('POSTGRESQL_DB')
POSTGRESQL_USER=os.getenv('POSTGRESQL_USER')
POSTGRESQL_PASSWORD=os.getenv('POSTGRESQL_PASSWORD')
POSTGRESQL_PORT=os.getenv('POSTGRESQL_PORT')

def fetch_data_as_json(query: str) -> str:
    """Execute a PostgreSQL query and return the results as a JSON array."""
    connection = None
    try:

        connection = psycopg.connect(
            host=POSTGRESQL_HOST,
            dbname=POSTGRESQL_DB,
            port=POSTGRESQL_PORT,
            user=POSTGRESQL_USER,
            password=POSTGRESQL_PASSWORD,
        )

        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        return json.dumps(results)
    except Exception as e:
        print(e)
        return json.dumps([])
    finally:
        if connection:
            cursor.close()
            connection.close()
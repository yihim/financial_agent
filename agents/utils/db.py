import sqlite3
from pathlib import Path
import os
from agents.constants.db import DB_FILE


# Establish connection to sqlite db
def connect_db(db_path: Path):

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        return conn, cursor
    except sqlite3.Error as e:
        print(f"Error connecting to database when executing 'connect_db': {e}")
        return None, None


# Execute sql query and get results from db
def execute_sql_query(conn, cursor, query):

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        formatted_results = [dict(zip(columns, row)) for row in rows]

    except sqlite3.DatabaseError as e:
        print(f"Database error when executing 'execute_sql_query': {e}")
        formatted_results = []

    except Exception as e:
        print(f"Unexpected error occurred when executing 'execute_sql_query': {e}")
        formatted_results = []

    finally:
        conn.close()

    return formatted_results


# Get transactions table schema
def get_table_schema(db_path: Path):
    conn, cursor = connect_db(db_path=db_path)
    table_schema = "table: transactions\n"

    if conn and cursor:
        try:
            cursor.execute("PRAGMA table_info(transactions);")
            schema = cursor.fetchall()
            for col in schema:
                table_schema += f"- {col[1]}: {col[2]}\n"

        except sqlite3.DatabaseError as e:
            print(f"Database error when executing 'get_table_schema': {e}")

        except Exception as e:
            print(f"Unexpected error occurred when executing 'get_table_schema': {e}")

        finally:
            conn.close()

        return table_schema
    else:
        return table_schema


# Check whether a specific client having multiple banks and accounts
def get_bank_and_account_ids(client_id: int, db_path: Path):
    conn, cursor = connect_db(db_path=db_path)
    if conn and cursor:
        try:
            query = """
                SELECT 
                    MIN(bank_id) AS bank_id,
                    MIN(account_id) AS account_id,
                    COUNT(DISTINCT bank_id) AS bank_count,
                    COUNT(DISTINCT account_id) AS account_count
                FROM transactions
                WHERE client_id = ?
            """
            cursor.execute(query, (client_id,))
            result = cursor.fetchone()
            if result and result[2] == 1 and result[3] == 1:
                bank_id, account_id = result[0], result[1]
                return bank_id, account_id
            else:
                return None
        finally:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    # print(root_dir)
    os.chdir(root_dir)
    db_path = root_dir / DB_FILE
    conn, cursor = connect_db(db_path=db_path)
    if conn and cursor:
        # sql_query = "SELECT category, SUM(debit) AS total_savings FROM transactions WHERE client_id = 2 AND bank_id = 1 AND account_id = 1 AND transaction_date >= '2023-07-01' AND transaction_date < '2023-08-01' GROUP BY category ORDER BY total_savings DESC LIMIT 3;"
        # results = execute_sql_query(conn=conn, cursor=cursor, query=sql_query)
        # print(results)

        results = get_bank_and_account_ids(client_id=31, db_path=db_path)
        if results:
            print(results)
        else:
            print("Multiple banks and accounts.")

    # print(get_table_schema(db_path=db_path))

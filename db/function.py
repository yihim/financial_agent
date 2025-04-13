import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# Establish connection to sqlite db
def connect_db(db_path: Path):

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        return conn, cursor
    except sqlite3.Error as e:
        logger.info(f"Error connecting to database when executing 'connect_db': {e}")
        return None, None


# Get transactions table schema
def get_table_schema(db_path: Path):
    table_schema = ""
    conn, cursor = connect_db(db_path=db_path)

    if conn and cursor:
        try:
            cursor.execute("PRAGMA table_info(transactions);")
            schema = cursor.fetchall()
            table_schema = "table: transactions\n"
            for col in schema:
                table_schema += f"- {col[1]}: {col[2]}\n"

        except sqlite3.DatabaseError as e:
            logger.info(
                f"Database error occurred when executing 'get_table_schema': {e}"
            )

        finally:
            cursor.close()
            conn.close()

        return table_schema
    else:
        return "Database connection failed."


# Execute sql query and get results from sqlite db
def execute_sql_query(db_path: Path, query: str):
    conn, cursor = connect_db(db_path=db_path)

    if not conn and not cursor:
        return {"status": "error", "message": "Database connection failed."}

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        formatted_results = [dict(zip(columns, row)) for row in rows]
        return {"status": "success", "formatted_results": formatted_results}

    except sqlite3.DatabaseError as e:
        return {
            "status": "error",
            "message": f"Database error occurred when executing execute_sql_query: {e}",
        }

    finally:
        cursor.close()
        conn.close()


# Check whether a specific client having multiple banks and accounts
def get_client_with_single_bank_and_account_id(db_path: Path, client_id: int):
    conn, cursor = connect_db(db_path=db_path)

    if not conn and not cursor:
        return {"status": "error", "message": "Database connection failed."}

    try:
        # Check banks and accounts
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

        if result[2] == 1 and result[3] == 1:
            # Client has exactly one bank and one account
            bank_id, account_id = result[0], result[1]
            return {"status": "success", "bank_id": bank_id, "account_id": account_id}
        else:
            # Client has multiple banks and/or accounts
            return {
                "status": "conflict",
                "message": f"Client ID-{client_id} has {result[2]} banks and {result[3]} accounts.",
            }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"Database error occurred when executing get_single_bank_and_account_ids: {e}",
        }

    finally:
        cursor.close()
        conn.close()


def validify_client_bank_account_ids(
    db_path: Path, client_id: int, bank_id: int = None, account_id: int = None
):
    conn, cursor = connect_db(db_path=db_path)

    if not conn or not cursor:
        return {"status": "error", "message": "Database connection failed."}

    try:
        # First check if client exists
        client_check_query = "SELECT COUNT(*) FROM transactions WHERE client_id = ?"
        cursor.execute(client_check_query, (client_id,))
        client_exists = cursor.fetchone()[0] > 0

        if not client_exists:
            return {
                "status": "error",
                "message": f"Client ID-{client_id} does not exist.",
            }

        if bank_id and account_id:
            # Second check if client-bank exists
            client_bank_check_query = (
                "SELECT COUNT(*) FROM transactions WHERE client_id = ? AND bank_id = ?"
            )
            cursor.execute(
                client_bank_check_query,
                (
                    client_id,
                    bank_id,
                ),
            )
            client_bank_exists = cursor.fetchone()[0] > 0

            if not client_bank_exists:
                return {
                    "status": "error",
                    "message": f"Client ID-{client_id} exists, but Bank ID-{bank_id} does not.",
                }

            # Third check if client-bank-account exists
            client_bank_account_check_query = "SELECT COUNT(*) FROM transactions WHERE client_id = ? AND bank_id = ? AND account_id = ?"
            cursor.execute(
                client_bank_account_check_query,
                (
                    client_id,
                    bank_id,
                    account_id,
                ),
            )
            client_bank_account_exists = cursor.fetchone()[0] > 0

            if not client_bank_account_exists:
                return {
                    "status": "error",
                    "message": f"Client ID-{client_id}, Bank ID-{bank_id}, and Account ID-{account_id} combination does not exist.",
                }

        return {"status": "success"}

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"Database error occurred when executing validify_client_bank_account_ids: {e}",
        }

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent
    db_path = root_dir / "transactions.db"

    # Test get_table_schema
    print(get_table_schema(db_path=db_path))

    # Test execute_sql_query
    sql_query = "SELECT category, SUM(COALESCE(debit, 0)) AS total_savings FROM transactions WHERE client_id = 2 AND bank_id = 1 AND account_id = 1 AND transaction_date >= '2023-07-01' AND transaction_date < '2023-08-01' GROUP BY category ORDER BY total_savings DESC LIMIT 3;"
    print(execute_sql_query(db_path=db_path, query=sql_query))

    # Test get_client_with_single_bank_and_account_id
    print(get_client_with_single_bank_and_account_id(client_id=6, db_path=db_path))

    # Test validify_client_bank_account_ids
    print(
        validify_client_bank_account_ids(
            db_path=db_path, client_id=880, bank_id=458, account_id=523
        )
    )

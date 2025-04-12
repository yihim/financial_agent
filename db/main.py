from function import (
    get_client_with_single_bank_and_account_id,
    validify_client_bank_account_ids,
    execute_sql_query,
)
from fastapi import FastAPI
import uvicorn
from pathlib import Path
from pydantic import BaseModel
from typing import Dict
import logging
import warnings
import sys

warnings.filterwarnings("ignore")

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

app = FastAPI(
    title="Transactions Database API",
    description="APIs for executing SQL queries, get bank and account ids, validify ids and check health",
    version="1.0.0",
)

ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "transactions.db"


class ValidifyIDRequest(BaseModel):
    client_id: int
    bank_id: int = None
    account_id: int = None


class ExecuteQueryRequest(BaseModel):
    sql_query: str


@app.post("/api/clients/validify/bank-account", response_model=Dict)
def validify_client_bank_account(request: ValidifyIDRequest):
    return validify_client_bank_account_ids(
        db_path=DB_PATH,
        client_id=request.client_id,
        bank_id=request.bank_id,
        account_id=request.account_id,
    )


@app.post("/api/db/execute-query", response_model=Dict)
def process_sql_query(request: ExecuteQueryRequest):
    return execute_sql_query(db_path=DB_PATH, query=request.sql_query)


@app.get("/api/clients/{client_id}/bank-account", response_model=Dict)
def get_client_bank_account(client_id: int):
    return get_client_with_single_bank_and_account_id(
        db_path=DB_PATH, client_id=client_id
    )


@app.get("/api/health", response_model=Dict)
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8070, reload=True)

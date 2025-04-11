import warnings
import logging
from ensemble_agents import create_multi_agents
import sys
from typing import List, Union, AsyncGenerator
import json
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pathlib import Path
from agents.constants.db import DB_FILE
from agents.utils.db import get_single_bank_and_account_ids
import uvicorn

warnings.filterwarnings("ignore")

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


# Function to decode messages
def decode_messages(json_str: str) -> List[Union[HumanMessage, AIMessage]]:
    """Decode a JSON string back to a list of message objects"""
    data = json.loads(json_str)
    result = []

    for item in data:
        if item.get("type") == "human":
            result.append(
                HumanMessage(
                    content=item["content"],
                    additional_kwargs=item.get("additional_kwargs", {}),
                )
            )
        elif item.get("type") == "ai":
            result.append(
                AIMessage(
                    content=item["content"],
                    additional_kwargs=item.get("additional_kwargs", {}),
                )
            )

    return result


class AgentsRequest(BaseModel):
    query: str
    chat_history: str
    thread_id: str
    client_id: int
    bank_id: int
    account_id: int


app = FastAPI(
    title="Agents API", description="API for responding queries", version="1.0.0"
)

root_dir = Path(__file__).resolve().parent
db_path = root_dir / DB_FILE
graph = create_multi_agents(db_path=db_path)


async def generate_stream(request: AgentsRequest) -> AsyncGenerator[str, None]:
    config = {"configurable": {"thread_id": request.thread_id}}

    chat_history_decoded = decode_messages(request.chat_history)

    state = {
        "messages": chat_history_decoded,
        "query": request.query,
        "query_classified_result": "",
        "query_classified_reason": "",
        "rewritten_query": "",
        "client_id": request.client_id,
        "account_id": request.account_id,
        "bank_id": request.bank_id,
        "action_plan": ["abc"],
        "query_understanding": "",
        "expected_output_structure": "",
        "sql_query": "",
        "database_results": [{"abc": 123}],
        "response_check_result": "",
        "response_check_result_reasoning": "",
        "answer": "",
    }

    async for msg, metadata in graph.astream(
        input=state, config=config, stream_mode="messages"
    ):
        if msg.content:
            yield msg.content


@app.post("/api/chat")
async def response_query(request: AgentsRequest):
    return StreamingResponse(
        generate_stream(request),
        media_type="text/plain",  # for text streaming
    )


@app.get("/api/clients/{client_id}/bank-account")
def get_client_bank_account(client_id: int):
    result = get_single_bank_and_account_ids(client_id=client_id, db_path=db_path)
    # Handle the different return types
    if isinstance(result, tuple) and len(result) == 2:
        # Client has single bank and account
        bank_id, account_id = result
        return {
            "status": "success",
            "client_id": client_id,
            "bank_id": bank_id,
            "account_id": account_id,
        }
    elif isinstance(result, str):
        # Error message returned
        if "does not exist" in result:
            # Client doesn't exist
            return {"status": "error", "message": result}
        else:
            # Client has multiple banks/accounts
            return {"status": "error", "message": result}
    else:
        # Unexpected error
        return {"status": "error", "message": "An unexpected error occurred"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("agents.api:app", host="0.0.0.0", port=8080, reload=True)

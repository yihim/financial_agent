import warnings
import logging
from function import create_multi_agents
import sys
from typing import List, Union, AsyncGenerator
import json
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
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
    title="Financial Chatbot API",
    description="APIs for responding queries and check health",
    version="1.0.0",
)


graph = create_multi_agents()


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
        "action_plan": [],
        "query_understanding": "",
        "expected_output_structure": "",
        "sql_query": "",
        "database_results": [],
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


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

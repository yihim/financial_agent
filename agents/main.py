import os
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
from langchain_community.callbacks.manager import get_openai_callback
from time import perf_counter

# Filter unwanted warnings
warnings.filterwarnings("ignore")

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


# To decode the encoded messages from the request payload
def decode_messages(json_str: str) -> List[Union[HumanMessage, AIMessage]]:
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


# Create expected request payload to respond to user queries
class AgentsRequest(BaseModel):
    query: str
    chat_history: str
    thread_id: str
    client_id: int
    bank_id: int
    account_id: int


# Initialize fastapi
app = FastAPI(
    title="Financial Chatbot API",
    description="APIs for responding queries and check health",
    version="1.0.0",
)

# Initialize the graph
graph = create_multi_agents()


async def generate_stream(request: AgentsRequest) -> AsyncGenerator[str, None]:
    # Create config to track the graph states
    config = {"configurable": {"thread_id": request.thread_id}}

    # To convert the encoded messages back to expected format for the llm
    chat_history_decoded = decode_messages(request.chat_history)

    # Initialize graph states
    state = {
        "messages": chat_history_decoded,
        "query": request.query,
        "query_classified_result": "",
        "query_classified_reason": "",
        "rewritten_query": "",
        "rewritten_query_reason": "",
        "client_id": request.client_id,
        "account_id": request.account_id,
        "bank_id": request.bank_id,
        "action_plan": [],
        "query_understanding": "",
        "expected_output_structure": "",
        "sql_query": "",
        "database_results": [],
        "answer": "",
    }

    start = perf_counter()

    # Initialize openai callback function to track tokens and costs info
    with get_openai_callback() as cb:

        # Stream the response
        async for msg, metadata in graph.astream(
            input=state, config=config, stream_mode="messages"
        ):
            if msg.content:
                yield msg.content

        logger.info(f"Total Tokens: {cb.total_tokens}")
        logger.info(f"Prompt Tokens: {cb.prompt_tokens}")
        logger.info(f"Completion Tokens: {cb.completion_tokens}")
        logger.info(f"Total Cost (USD): ${cb.total_cost}\n")

    logger.info(graph.get_state(config).values)

    # Create log files per thread_id-client_id-bank_id-account_id
    logs_dir = "./logs"
    file_path = f"{logs_dir}/{request.thread_id}-{request.client_id}-{request.bank_id}-{request.account_id}.json"
    final_state = graph.get_state(config).values
    current_log = {
        "user_query": final_state.get("query", ""),
        "bot_response": final_state.get("answer", ""),
        "time_taken": f"{perf_counter() - start:.2f} seconds",
        "graph_state_info": {
            "query_classified_result": final_state.get("query_classified_result", ""),
            "query_classified_reason": final_state.get("query_classified_reason", ""),
            "rewritten_query": final_state.get("rewritten_query", ""),
            "rewritten_query_reason": final_state.get("rewritten_query_reason", ""),
            "action_plan": str(final_state.get("action_plan", "")),
            "query_understanding": final_state.get("query_understanding", ""),
            "expected_output_structure": final_state.get(
                "expected_output_structure", ""
            ),
            "sql_query": final_state.get("sql_query", ""),
            "database_results": str(final_state.get("database_results", "")),
        },
        "openai_info": {
            "total_tokens": cb.total_tokens,
            "prompt_tokens": cb.prompt_tokens,
            "completion_tokens": cb.prompt_tokens,
            "total_cost": f"{cb.total_cost} USD",
        },
    }

    if os.path.exists(file_path):
        # If file exists, read and load it
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = [logs]
        except json.JSONDecodeError:
            logs = []
    else:
        # Else, initialize a new log for the new log file
        logs = []

    logs.append(current_log)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(logs, indent=4, fp=f)


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

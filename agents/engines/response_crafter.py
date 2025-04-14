from constants.models import RESPONSE_CRAFTER_SYSTEM_PROMPT
from utils.models import load_llm
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Any
from langchain_core.runnables import RunnableConfig
import logging

logger = logging.getLogger(__name__)


# To enable stream response
# Remove 'config' param and change 'ainvoke' to 'invoke' for testing
async def craft_response(
    llm,
    rewritten_query: str,
    database_results: List[Dict[str, Any]],
    config: RunnableConfig,
) -> str:
    prompt = ChatPromptTemplate.from_messages(
        ("system", RESPONSE_CRAFTER_SYSTEM_PROMPT)
    )
    chain = prompt | llm

    try:
        response = await chain.ainvoke(
            {"rewritten_query": rewritten_query, "database_results": database_results},
            config=config,
        )
        return response.content
    except Exception as e:
        error_msg = f"Unexpected error occurred when executing 'craft_response': {e}"
        logger.info(error_msg)
        return error_msg


if __name__ == "__main__":
    # Test craft_response locally
    llm = load_llm()
    rewritten_query = "List the top 3 categories I saved most on July 2023"
    database_results = [
        {"category": "restaurants", "total_savings": 5536.862},
        {"category": "transfer deposit", "total_savings": 540.0},
        {"category": "uncategorized", "total_savings": 15.0},
    ]
    response = craft_response(
        llm=llm, rewritten_query=rewritten_query, database_results=database_results
    )
    if response is not None:
        print(response)

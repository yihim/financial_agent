from utils.models import load_llm
from constants.models import QUERY_REWRITER_SYSTEM_PROMPT
from constants.db import DB_TABLE_SCHEMA
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Union
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)


# Create a structured output for query_rewriter,
# making it clearer for the llm to response expectedly and easier to access response
class QueryRewriterOutput(BaseModel):
    rewritten_query: str = Field(
        ..., description="The explicit, context-independent rewritten query."
    )
    reasoning: str = Field(
        ..., description="Brief explanation of key transformations made and why."
    )


def rewrite_query(
    llm,
    query: str,
    chat_history: List[Union[HumanMessage, AIMessage]],
    rewritten_query: str,
) -> Union[QueryRewriterOutput, str]:
    prompt = ChatPromptTemplate.from_messages(("system", QUERY_REWRITER_SYSTEM_PROMPT))
    chain = prompt | llm

    try:
        response = chain.invoke(
            {
                "date_time": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "query": query,
                "chat_history": chat_history,
                "schema": DB_TABLE_SCHEMA,
                "rewritten_query": rewritten_query,
            }
        )
        return response
    except Exception as e:
        error_msg = f"Unexpected error occurred when executing 'rewrite_query': {e}"
        logger.info(error_msg)
        return error_msg


if __name__ == "__main__":
    # Test rewrite_query locally
    llm = load_llm()
    llm = llm.with_structured_output(QueryRewriterOutput)
    query = "List the top 3 categories I spent most on last month"
    chat_history = [HumanMessage(content=query)]
    rewritten_query = ""
    response = rewrite_query(
        llm=llm, query=query, chat_history=chat_history, rewritten_query=rewritten_query
    )
    if response is not None:
        print(response.rewritten_query)
        print(response.reasoning)

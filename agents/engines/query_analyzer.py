from utils.models import load_llm
from constants.models import QUERY_ANALYZER_SYSTEM_PROMPT
from constants.db import DB_TABLE_SCHEMA
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from typing import Literal, List, Union, Optional
from langchain_core.messages import HumanMessage, AIMessage


class QueryAnalyzerOutput(BaseModel):
    classified_result: Literal[
        "ambiguous", "sensitive", "general", "valid_transactional"
    ] = Field(..., description="The classified result from the user query.")
    classified_reason: str = Field(
        ..., description="Detailed explanation of why this classification was chosen."
    )


def analyze_query(
    llm, query: str, chat_history: List[Union[HumanMessage, AIMessage]]
) -> Optional[QueryAnalyzerOutput]:
    prompt = ChatPromptTemplate.from_messages(("system", QUERY_ANALYZER_SYSTEM_PROMPT))

    chain = prompt | llm

    try:
        response = chain.invoke(
            {"chat_history": chat_history, "query": query, "schema": DB_TABLE_SCHEMA}
        )
        return response
    except Exception as e:
        print(f"Unexpected error occurred when executing 'analyze_query': {e}")
        return None


if __name__ == "__main__":
    llm = load_llm()
    llm = llm.with_structured_output(QueryAnalyzerOutput)
    query = "List my transactions for that thing I bought"
    chat_history = [HumanMessage(content=query)]
    response = analyze_query(llm=llm, query=query, chat_history=chat_history)
    if response is not None:
        print(response.classified_result)
        print(response.classified_reason)

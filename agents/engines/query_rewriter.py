from agents.utils.models import load_llm
from agents.constants.models import QUERY_REWRITER_SYSTEM_PROMPT
from agents.constants.db import DB_TABLE_SCHEMA
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Union, Optional


class QueryRewriterOutput(BaseModel):
    rewritten_query: str = Field(
        ..., description="The explicit, context-independent rewritten query."
    )
    reasoning: str = Field(
        ..., description="Brief explanation of key transformations made and why."
    )


def rewrite_query(
    llm, query: str, chat_history: List[Union[HumanMessage, AIMessage]]
) -> Optional[QueryRewriterOutput]:
    prompt = ChatPromptTemplate.from_messages(("system", QUERY_REWRITER_SYSTEM_PROMPT))
    chain = prompt | llm

    try:
        response = chain.invoke(
            {"query": query, "chat_history": chat_history, "schema": DB_TABLE_SCHEMA}
        )
        return response
    except Exception as e:
        print(f"Unexpected error occurred when executing 'rewrite_query': {e}")
        return None


if __name__ == "__main__":
    llm = load_llm()
    llm = llm.with_structured_output(QueryRewriterOutput)
    query = "List the top 3 categories I spent most on last month"
    chat_history = [HumanMessage(content=query)]
    response = rewrite_query(llm=llm, query=query, chat_history=chat_history)
    if response is not None:
        print(response.rewritten_query)
        print(response.reasoning)

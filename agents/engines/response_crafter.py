from agents.constants.models import RESPONSE_CRAFTER_SYSTEM_PROMPT
from agents.utils.models import load_llm
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Optional, Any


def craft_response(
    llm, rewritten_query: str, database_result: List[Dict[str, Any]]
) -> Optional[str]:
    prompt = ChatPromptTemplate.from_messages(
        ("system", RESPONSE_CRAFTER_SYSTEM_PROMPT)
    )
    chain = prompt | llm

    try:
        response = chain.invoke(
            {"rewritten_query": rewritten_query, "database_result": database_result}
        )
        return response.content
    except Exception as e:
        print(f"Unexpected error occurred when executing 'craft_response': {e}")
        return None


if __name__ == "__main__":
    llm = load_llm()
    rewritten_query = "List the top 3 categories I saved most on July 2023"
    database_result = []
    response = craft_response(llm=llm, rewritten_query=rewritten_query, database_result=database_result)
    if response is not None:
        print(response)

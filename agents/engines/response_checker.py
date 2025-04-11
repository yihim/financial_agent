from agents.constants.models import RESPONSE_CHECKER_SYSTEM_PROMPT
from agents.utils.models import load_llm
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional, List, Dict, Any


class ResponseCheckerOutput(BaseModel):
    check_result: str = Field(
        ...,
        description="This field must contain 'yes' if the provided database results fully address the user query, or 'no' if it does not.",
    )
    reasoning: str = Field(
        ..., description="The reason of why the check result is made."
    )


def check_response(
    llm, rewritten_query: str, database_results: List[Dict[str, Any]]
) -> Optional[ResponseCheckerOutput]:
    prompt = ChatPromptTemplate.from_messages(
        ("system", RESPONSE_CHECKER_SYSTEM_PROMPT)
    )
    chain = prompt | llm

    try:
        response = chain.invoke(
            {"rewritten_query": rewritten_query, "database_results": database_results}
        )
        return response
    except Exception as e:
        print(f"Unexpected error occurred when executing 'check_response': {e}")
        return None


if __name__ == "__main__":
    llm = load_llm()
    llm = llm.with_structured_output(ResponseCheckerOutput)
    rewritten_query = "List the top 3 categories I saved most on July 2023"
    database_results = [
        {"category": "restaurants", "total_savings": 5536.862},
        {"category": "transfer deposit", "total_savings": 540.0},
        {"category": "uncategorized", "total_savings": 15.0},
    ]
    response = check_response(
        llm=llm, rewritten_query=rewritten_query, database_results=database_results
    )
    if response is not None:
        print(response.check_result)
        print(response.reasoning)

from agents.constants.models import RESPONSE_CHECKER_SYSTEM_PROMPT
from agents.utils.models import load_llm
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional


class ResponseCheckerOutput(BaseModel):
    check_result: str = Field(
        ...,
        description="This field must contain 'yes' if the provided answer fully addresses the user query, or 'no' if it does not.",
    )


def check_response(
    llm, rewritten_query: str, answer: str
) -> Optional[ResponseCheckerOutput]:
    prompt = ChatPromptTemplate.from_messages(
        ("system", RESPONSE_CHECKER_SYSTEM_PROMPT)
    )
    chain = prompt | llm

    try:
        response = chain.invoke({"rewritten_query": rewritten_query, "answer": answer})
        return response
    except Exception as e:
        print(f"Unexpected error occurred when executing 'check_response': {e}")
        return None


if __name__ == "__main__":
    llm = load_llm()
    llm = llm.with_structured_output(ResponseCheckerOutput)
    rewritten_query = "List the top 3 categories I saved most on July 2023"
    answer = """# Your Savings in July 2023

It looks like there are currently **no records** available for the top categories you saved in July 2023. This could be due to a few reasons:

- **No transactions recorded**: You may not have saved any money in that month.
- **Data not yet processed**: Sometimes, it takes a little while for all transactions to be updated in the system.
- **Filters applied**: Ensure that there are no filters set that might exclude relevant data.

### What You Can Do Next

Here are a few suggestions to help you find the information you need:

- **Check other months**: You might want to look at your savings in other months to see if there are any trends.
- **Review your overall spending**: Understanding where your money goes can help identify potential savings.
- **Adjust your query**: If you have specific categories in mind, try asking about those directly.

If you have any other questions or need assistance with a different query, feel free to ask!"""
    response = check_response(llm=llm, rewritten_query=rewritten_query, answer=answer)
    if response is not None:
        print(response.check_result)

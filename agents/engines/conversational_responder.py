from utils.models import load_llm
from constants.models import CONVERSATIONAL_RESPONDER_SYSTEM_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Union
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig


async def respond_conversational(
    llm: ChatOpenAI,
    query: str,
    classified_result: str,
    classified_reason: str,
    chat_history: List[Union[HumanMessage, AIMessage]],
    config: RunnableConfig,
) -> str:
    prompt = ChatPromptTemplate.from_messages(
        ("system", CONVERSATIONAL_RESPONDER_SYSTEM_PROMPT)
    )
    chain = prompt | llm

    try:
        response = await chain.ainvoke(
            {
                "query": query,
                "classified_result": classified_result,
                "classified_reason": classified_reason,
                "chat_history": chat_history,
            },
            config=config,
        )
        return response.content
    except Exception as e:
        print(f"Unexpected error occurred when executing 'respond_conversational': {e}")
        return str(e)


if __name__ == "__main__":
    llm = load_llm()
    query = "List my transactions for that thing I bought"
    classified_result = "ambiguous"
    classified_reason = "The query 'List my transactions for that thing I bought' lacks specific details such as the timeframe, the account from which the transaction was made, or the specific item purchased. The phrase 'that thing' is vague and does not provide enough context to identify which transaction the user is referring to."
    chat_history = [HumanMessage(content=query)]
    response = respond_conversational(
        llm=llm,
        query=query,
        classified_result=classified_result,
        classified_reason=classified_reason,
        chat_history=chat_history,
    )
    print(response)

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from constants.models import MODEL_NAME

# Load environment variables
load_dotenv()


def load_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        max_tokens=1024,
        temperature=0,
        max_retries=3,
        request_timeout=None,
        streaming=True,
        stream_usage=True,
    )

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from constants.models import MODEL_NAME
from langchain_redis import RedisSemanticCache
from langchain_openai import OpenAIEmbeddings
import redis

# Load environment variables
load_dotenv()


embeddings = OpenAIEmbeddings()

REDIS_URL = "redis://redis:6379"
redis_client = redis.from_url(url=REDIS_URL)
semantic_cache = RedisSemanticCache(
    redis_url=REDIS_URL,
    embeddings=embeddings,
    distance_threshold=0.2,
    ttl=86400,
)


def load_llm():
    return ChatOpenAI(
        model=MODEL_NAME,
        max_tokens=None,
        temperature=0,
        max_retries=3,
        request_timeout=None,
    )


def load_llm_with_stream() -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        max_tokens=None,
        temperature=0,
        max_retries=3,
        request_timeout=None,
        streaming=True,
        stream_usage=True,
    )


def load_llm_with_cache():
    return ChatOpenAI(
        model=MODEL_NAME,
        max_tokens=None,
        temperature=0,
        max_retries=3,
        request_timeout=None,
        cache=semantic_cache
    )
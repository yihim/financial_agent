from utils.models import load_llm
from constants.models import TASK_PLANNER_SYSTEM_PROMPT
from constants.db import DB_TABLE_SCHEMA
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)


# Created structured output for the subsequent tasks
class SubTask(BaseModel):
    step: str = Field(..., description="The number of step to be taken.")
    operation: str = Field(
        ..., description="Name of operation (SELECT, FILTER, JOIN, AGGREGATE, etc.)."
    )
    description: str = Field(..., description="Detailed description of this step.")
    fields_involved: List[str] = Field(..., description="The fields that required.")
    conditions: str = Field(
        ..., description="Any conditions or constraints for this step."
    )


# Create a structured output for task_planner,
# making it clearer for the llm to response expectedly and easier to access response
class TaskPlannerOutput(BaseModel):
    query_understanding: str = Field(
        ...,
        description="Brief interpretation of what the rewritten query is asking for.",
    )
    execution_plan: List[SubTask] = Field(
        ...,
        description="The decomposed sequential of well-defined and structured sub-tasks",
    )
    expected_output_structure: str = Field(
        ..., description="Description of what the final result should look like"
    )


def plan_task(
    llm, rewritten_query: str, client_id: int, bank_id: int, account_id: int
) -> Optional[TaskPlannerOutput, str]:
    prompt = ChatPromptTemplate.from_messages(("system", TASK_PLANNER_SYSTEM_PROMPT))
    chain = prompt | llm

    try:
        response = chain.invoke(
            {
                "client_id": client_id,
                "bank_id": bank_id,
                "account_id": account_id,
                "date_time": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "rewritten_query": rewritten_query,
                "schema": DB_TABLE_SCHEMA,
            }
        )
        return response
    except Exception as e:
        error_msg = f"Unexpected error occurred when executing 'plan_task': {e}"
        logger.info(error_msg)
        return error_msg


if __name__ == "__main__":
    # Test plan_task locally
    llm = load_llm()
    llm = llm.with_structured_output(TaskPlannerOutput)
    client_id = 2
    bank_id = 1
    account_id = 1
    rewritten_query = "List the top 3 categories I saved most on July 2023"
    response = plan_task(
        llm=llm,
        rewritten_query=rewritten_query,
        client_id=client_id,
        bank_id=bank_id,
        account_id=account_id,
    )
    if response is not None:
        print(response.query_understanding)
        print(response.execution_plan)
        print(response.expected_output_structure)

from agents.utils.models import load_llm
from agents.constants.models import SQL_QUERY_GENERATOR_SYSTEM_PROMPT
from agents.constants.db import DB_TABLE_SCHEMA
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
import os
from agents.engines.task_planner import SubTask
from typing import List, Optional


class SqlQueryGeneratorOutput(BaseModel):
    sql_query: str = Field(..., description="The generated SQL query.")


def generate_sql_query(
    llm, rewritten_query: str, action_plan: List[SubTask]
) -> Optional[SqlQueryGeneratorOutput]:
    prompt = ChatPromptTemplate.from_messages(
        ("system", SQL_QUERY_GENERATOR_SYSTEM_PROMPT)
    )
    chain = prompt | llm

    try:
        response = chain.invoke(
            {
                "rewritten_query": rewritten_query,
                "schema": DB_TABLE_SCHEMA,
                "action_plan": action_plan,
            }
        )
        return response
    except Exception as e:
        print(f"Unexpected error occurred when executing 'generate_sql_query': {e}")
        return None


if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)
    llm = load_llm()
    llm = llm.with_structured_output(SqlQueryGeneratorOutput)
    rewritten_query = "List the top 3 categories I saved most on July 2023"
    action_plan = [
        SubTask(
            step="1",
            operation="FILTER",
            description="Filter transactions to include only those from July 2023 for the specified client, bank, and account.",
            fields_involved=["client_id", "bank_id", "account_id", "transaction_date"],
            conditions="transaction_date >= '2023-07-01 00:00:00' AND transaction_date < '2023-08-01 00:00:00' AND client_id = 2 AND bank_id = 1 AND account_id = 1",
        ),
        SubTask(
            step="2",
            operation="AGGREGATE",
            description="Aggregate the filtered transactions by category, summing the debit amounts to determine total savings per category.",
            fields_involved=["category", "debit"],
            conditions="Use the results from step 1",
        ),
        SubTask(
            step="3",
            operation="SORT",
            description="Sort the aggregated results in descending order based on the total savings calculated in step 2.",
            fields_involved=["category", "total_savings"],
            conditions="Sort by total_savings DESC",
        ),
        SubTask(
            step="4",
            operation="LIMIT",
            description="Limit the results to the top 3 categories with the highest savings.",
            fields_involved=["category", "total_savings"],
            conditions="Limit results to 3",
        ),
    ]
    response = generate_sql_query(
        llm=llm,
        rewritten_query=rewritten_query,
        action_plan=action_plan,
    )
    if response is not None:
        print(response.sql_query)

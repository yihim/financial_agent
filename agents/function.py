from utils.models import load_llm
from constants.db import DB_EXECUTE_SQL_QUERY_URL
from engines.query_analyzer import QueryAnalyzerOutput, analyze_query
from engines.query_rewriter import QueryRewriterOutput, rewrite_query
from engines.task_planner import TaskPlannerOutput, plan_task
from engines.sql_query_generator import (
    SqlQueryGeneratorOutput,
    generate_sql_query,
)
from engines.response_crafter import craft_response
from engines.conversational_responder import respond_conversational
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage
from typing import TypedDict, List, Union, Any, Literal
import requests
import logging


logger = logging.getLogger(__name__)


# State management for the agents
class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]
    query: str
    query_classified_result: str
    query_classified_reason: str
    rewritten_query: str
    rewritten_query_reason: str
    client_id: int
    bank_id: int
    account_id: int
    action_plan: List[Any]
    query_understanding: str
    expected_output_structure: str
    sql_query: str
    database_results: List[Any]
    answer: str


def create_multi_agents() -> StateGraph.compile:
    # Initialize memory
    memory = MemorySaver()

    llm = load_llm()

    def execute_analyze_query(state: AgentState):
        analyze_result = analyze_query(
            llm=llm.with_structured_output(QueryAnalyzerOutput),
            query=state["query"],
            chat_history=state["messages"],
        )
        logger.info(f"Query Analyze Result: {analyze_result.classified_result}\n\n")
        return {
            "query_classified_result": analyze_result.classified_result,
            "query_classified_reason": analyze_result.classified_reason,
        }

    def execute_rewrite_query(state: AgentState):
        rewrite_result = rewrite_query(
            llm=llm.with_structured_output(QueryRewriterOutput),
            query=state["query"],
            chat_history=state["messages"],
            rewritten_query=state["rewritten_query"],
        )
        logger.info(f"Rewritten Query: {rewrite_result.rewritten_query}")
        logger.info(f"Rewritten Reason: {rewrite_result.reasoning}\n\n")
        return {
            "rewritten_query": rewrite_result.rewritten_query,
            "rewritten_query_reason": rewrite_result.reasoning,
        }

    def execute_plan_task(state: AgentState):
        action_plan = plan_task(
            llm=llm.with_structured_output(TaskPlannerOutput),
            rewritten_query=state["rewritten_query"],
            client_id=state["client_id"],
            bank_id=state["bank_id"],
            account_id=state["account_id"],
        )
        logger.info(f"Query Understanding: {action_plan.query_understanding}")
        logger.info(f"Action Plan: {action_plan.execution_plan}")
        logger.info(
            f"Expected Output Structure: {action_plan.expected_output_structure}\n\n"
        )
        return {
            "action_plan": action_plan.execution_plan,
            "query_understanding": action_plan.query_understanding,
            "expected_output_structure": action_plan.expected_output_structure,
        }

    def execute_generate_sql_query(state: AgentState):
        sql_query = generate_sql_query(
            llm=llm.with_structured_output(SqlQueryGeneratorOutput),
            rewritten_query=state["rewritten_query"],
            action_plan=state["action_plan"],
            query_understanding=state["query_understanding"],
            expected_output_structure=state["expected_output_structure"],
            client_id=state["client_id"],
            bank_id=state["bank_id"],
            account_id=state["account_id"],
        )
        logger.info(f"SQL Query: {sql_query.sql_query}\n\n")
        return {"sql_query": sql_query.sql_query}

    def execute_sql_query_in_db(state: AgentState):
        db_result = []
        db_response = requests.post(
            url=DB_EXECUTE_SQL_QUERY_URL, json={"sql_query": state["sql_query"]}
        )
        if db_response.status_code == 200 and db_response.json()["status"] == "success":
            db_result = db_response.json()["formatted_results"]
            logger.info(f"Database Results: {db_result}")
            return {"database_results": db_result}
        else:
            return {"database_results": db_result}

    async def execute_craft_response(state: AgentState, config: RunnableConfig):
        answer = await craft_response(
            llm=llm,
            rewritten_query=state["rewritten_query"],
            database_results=state["database_results"],
            config=config,
        )
        return {"answer": answer}

    async def execute_respond_conversational(state: AgentState, config: RunnableConfig):
        response = await respond_conversational(
            llm=llm,
            query=state["query"],
            classified_result=state["query_classified_result"],
            classified_reason=state["query_classified_reason"],
            chat_history=state["messages"],
            config=config,
        )
        return {"answer": response}

    # Routing to either a conversational path or technical path based on the classified query
    def initial_routing(state: AgentState) -> Literal["rewrite", "conversational"]:
        if state["query_classified_result"] == "valid_transactional":
            return "rewrite"
        else:
            return "conversational"

    workflow = StateGraph(AgentState)

    workflow.add_node("query_analyzer", execute_analyze_query)
    workflow.add_node("conversational_responder", execute_respond_conversational)
    workflow.add_node("query_rewriter", execute_rewrite_query)
    workflow.add_node("task_planner", execute_plan_task)
    workflow.add_node("sql_query_generator", execute_generate_sql_query)
    workflow.add_node("sql_query_executor", execute_sql_query_in_db)
    workflow.add_node("response_crafter", execute_craft_response)

    workflow.add_conditional_edges(
        "query_analyzer",
        initial_routing,
        {"rewrite": "query_rewriter", "conversational": "conversational_responder"},
    )

    workflow.add_edge("query_rewriter", "task_planner")
    workflow.add_edge("task_planner", "sql_query_generator")
    workflow.add_edge("sql_query_generator", "sql_query_executor")
    workflow.add_edge("sql_query_executor", "response_crafter")

    workflow.add_edge("conversational_responder", END)
    workflow.add_edge("response_crafter", END)

    workflow.set_entry_point("query_analyzer")

    app = workflow.compile(checkpointer=memory)

    return app


if __name__ == "__main__":
    # Create graph visualization image
    from langchain_core.runnables.graph import MermaidDrawMethod
    from IPython.display import Image

    graph = create_multi_agents()
    try:
        img = Image(
            graph.get_graph().draw_mermaid_png(
                draw_method=MermaidDrawMethod.API,
            )
        )

        with open("./graph_visualization.png", "wb") as f:
            f.write(img.data)
    except Exception as e:
        print(f"Unexpected error occurred: {e}")

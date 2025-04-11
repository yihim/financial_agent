from agents.utils.models import load_llm
from agents.utils.db import (
    connect_db,
    execute_sql_query,
    get_single_bank_and_account_ids,
)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnableConfig
from typing import TypedDict, List, Union, Dict, Any, Literal
from langchain_core.messages import HumanMessage, AIMessage
from agents.engines.query_analyzer import QueryAnalyzerOutput, analyze_query
from agents.engines.query_rewriter import QueryRewriterOutput, rewrite_query
from agents.engines.task_planner import TaskPlannerOutput, plan_task, SubTask
from agents.engines.sql_query_generator import (
    SqlQueryGeneratorOutput,
    generate_sql_query,
)
from agents.engines.response_crafter import craft_response
from agents.engines.response_checker import ResponseCheckerOutput, check_response
from agents.engines.conversational_responder import respond_conversational
from pathlib import Path
from agents.constants.db import DB_FILE
import logging
import asyncio


class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]
    query: str
    query_classified_result: str
    query_classified_reason: str
    rewritten_query: str
    client_id: int
    bank_id: int
    account_id: int
    action_plan: List[Any]
    query_understanding: str
    expected_output_structure: str
    sql_query: str
    database_results: List[Dict[str, Any]]
    response_check_result: str
    response_check_result_reasoning: str
    answer: str


def create_multi_agents(db_path: Path) -> StateGraph.compile:
    memory = MemorySaver()

    llm = load_llm()

    def execute_analyze_query(state: AgentState):
        print(f"Chat History: {state['messages']}")
        analyze_result = analyze_query(
            llm=llm.with_structured_output(QueryAnalyzerOutput),
            query=state["query"],
            chat_history=state["messages"],
        )
        print(f"Query Analyze Result: {analyze_result.classified_result}\n\n")
        return {
            "query_classified_result": analyze_result.classified_result,
            "query_classified_reason": analyze_result.classified_reason,
        }

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

    def execute_rewrite_query(state: AgentState):
        rewrite_result = rewrite_query(
            llm=llm.with_structured_output(QueryRewriterOutput),
            query=state["query"],
            chat_history=state["messages"],
            rewritten_query=state["rewritten_query"],
            response_check_result=state["response_check_result"],
            response_check_result_reasoning=state["response_check_result_reasoning"],
        )
        print(f"Rewritten Query: {rewrite_result.rewritten_query}")
        print(f"Rewritten Reason: {rewrite_result.reasoning}\n\n")
        return {"rewritten_query": rewrite_result.rewritten_query}

    def execute_plan_task(state: AgentState):
        action_plan = plan_task(
            llm=llm.with_structured_output(TaskPlannerOutput),
            rewritten_query=state["rewritten_query"],
            client_id=state["client_id"],
            bank_id=state["bank_id"],
            account_id=state["account_id"],
        )
        print(f"Query Understanding: {action_plan.query_understanding}")
        print(f"Action Plan: {action_plan.execution_plan}")
        print(f"Expected Output Structure: {action_plan.expected_output_structure}\n\n")
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
        print(f"SQL Query: {sql_query.sql_query}\n\n")
        return {"sql_query": sql_query.sql_query}

    def execute_validate_sql_query(state: AgentState):
        conn, cursor = connect_db(db_path=db_path)
        database_results = []
        if conn and cursor:
            database_results = execute_sql_query(
                conn=conn, cursor=cursor, query=state["sql_query"]
            )
            print(f"Database Results: {database_results}\n\n")
            return {"database_results": database_results}
        else:
            print(f"Database Results: {database_results}\n\n")
            return {"database_results": database_results}

    async def execute_craft_response(state: AgentState, config: RunnableConfig):
        answer = await craft_response(
            llm=llm,
            rewritten_query=state["rewritten_query"],
            database_results=state["database_results"],
            config=config,
        )
        return {"answer": answer}

    def execute_check_response(state: AgentState):
        check_result = check_response(
            llm=llm.with_structured_output(ResponseCheckerOutput),
            rewritten_query=state["rewritten_query"],
            database_results=state["database_results"],
        )
        print(
            f"Check Result for '{state['database_results']}' is '{check_result.check_result}'"
        )
        print(f"Reasoning: {check_result.reasoning}\n\n")
        return {
            "response_check_result": check_result.check_result,
            "response_check_result_reasoning": check_result.reasoning,
        }

    def initial_routing(state: AgentState) -> Literal["rewrite", "conversational"]:
        if state["query_classified_result"] == "valid_transactional":
            return "rewrite"
        else:
            return "conversational"

    def is_accurate_response(state: AgentState) -> Literal["craft_response", "rewrite"]:

        if state["response_check_result"] == "yes":
            return "craft_response"
        else:
            return "rewrite"

    workflow = StateGraph(AgentState)

    workflow.add_node("query_analyzer", execute_analyze_query)
    workflow.add_node("conversational_responder", execute_respond_conversational)
    workflow.add_node("query_rewriter", execute_rewrite_query)
    workflow.add_node("task_planner", execute_plan_task)
    workflow.add_node("sql_query_generator", execute_generate_sql_query)
    workflow.add_node("sql_query_validator", execute_validate_sql_query)
    workflow.add_node("response_crafter", execute_craft_response)
    workflow.add_node("response_checker", execute_check_response)

    workflow.add_conditional_edges(
        "query_analyzer",
        initial_routing,
        {"rewrite": "query_rewriter", "conversational": "conversational_responder"},
    )

    workflow.add_edge("query_rewriter", "task_planner")
    workflow.add_edge("task_planner", "sql_query_generator")
    workflow.add_edge("sql_query_generator", "sql_query_validator")
    workflow.add_edge("sql_query_validator", "response_checker")

    workflow.add_conditional_edges(
        "response_checker",
        is_accurate_response,
        {"craft_response": "response_crafter", "rewrite": "query_rewriter"},
    )

    workflow.add_edge("conversational_responder", END)
    workflow.add_edge("response_crafter", END)

    workflow.set_entry_point("query_analyzer")

    app = workflow.compile(checkpointer=memory)

    return app


async def main():
    import uuid

    session_id = uuid.uuid4().hex[:8]
    config = {"configurable": {"thread_id": session_id}}

    root_dir = Path(__file__).resolve().parent
    db_path = root_dir / DB_FILE

    graph = create_multi_agents(db_path=db_path)

    session_messages = []

    client_id = 6
    results = get_single_bank_and_account_ids(client_id=client_id, db_path=db_path)
    if isinstance(results, tuple):
        bank_id = results[0]
        account_id = results[1]
    else:
        bank_id = 144
        account_id = 162

    while True:
        query = input("Query: ").strip()

        if query.lower() == "q":
            print(graph.get_state(config).values)
            break

        session_messages.append(HumanMessage(content=query))

        state = {
            "messages": session_messages,
            "query": query,
            "query_classified_result": "",
            "query_classified_reason": "",
            "rewritten_query": "",
            "client_id": client_id,
            "account_id": account_id,
            "bank_id": bank_id,
            "action_plan": ["abc"],
            "query_understanding": "",
            "expected_output_structure": "",
            "sql_query": "",
            "database_results": [{"abc": 123}],
            "response_check_result": "",
            "response_check_result_reasoning": "",
            "answer": "",
        }

        full_response = ""
        async for msg, metadata in graph.astream(
            input=state, config=config, stream_mode="messages"
        ):
            if msg.content:
                full_response += msg.content
                print(msg.content, end="", flush=True)
        print()

        session_messages.append(AIMessage(content=full_response))


if __name__ == "__main__":
    # Test graph
    asyncio.run(main())

    # # Create graph visualization
    # from langchain_core.runnables.graph import MermaidDrawMethod
    # from IPython.display import Image
    #
    # graph = create_multi_agents()
    # try:
    #     img = Image(
    #         graph.get_graph().draw_mermaid_png(
    #             draw_method=MermaidDrawMethod.API,
    #         )
    #     )
    #
    #     with open("graph_visualization.png", "wb") as f:
    #         f.write(img.data)
    # except Exception:
    #     pass

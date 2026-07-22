"""LangGraph StateGraph — the SQL Agent workflow orchestration layer.

This module is intentionally thin (< 100 lines).  It only connects
nodes and edges — no business logic lives here.

Usage:
    from app.graph.graph import build_graph

    graph = build_graph(analyzer=..., retriever=..., ...)
    result = await graph.ainvoke({"question": "销售额趋势", "max_retries": 3})
"""

from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.state import AgentState
from app.graph.nodes import (
    analyze_task_node,
    execute_sql_node,
    generate_sql_node,
    reflect_node,
    retrieve_schema_node,
    validate_sql_node,
)
from app.graph.routers import (
    route_after_execute,
    route_after_reflection,
    route_after_validate,
)


def _async_partial(fn, **kwargs):
    """Bind keyword arguments to an async node function.

    LangGraph nodes receive ``(state)``; this wrapper injects
    extra dependencies (analyzer, retriever, etc.) so the node
    never needs to import or construct them.
    """
    async def wrapper(state: AgentState) -> dict:
        return await fn(state, **kwargs)
    return wrapper


def build_graph(
    analyzer: object,
    retriever: object,
    generator: object,
    validator: object,
    executor: object,
    reflection: object,
) -> StateGraph:
    """Build and compile the SQL Agent workflow graph.

    Each node wraps a module injected from outside — making every
    node fully mockable in tests.
    """
    workflow = StateGraph(AgentState)

    # ── Nodes ─────────────────────────────────────────────
    workflow.add_node("analyze", _async_partial(analyze_task_node, analyzer=analyzer))
    workflow.add_node("retrieve", _async_partial(retrieve_schema_node, retriever=retriever))
    workflow.add_node("generate", _async_partial(generate_sql_node, generator=generator))
    workflow.add_node("validate", _async_partial(validate_sql_node, validator=validator))
    workflow.add_node("execute", _async_partial(execute_sql_node, executor=executor))
    workflow.add_node("reflect", _async_partial(reflect_node, reflection=reflection))

    # ── Edges ─────────────────────────────────────────────
    workflow.add_edge("analyze", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "validate")

    workflow.add_conditional_edges(
        "validate",
        route_after_validate,
        {"reflect": "reflect", "execute": "execute"},
    )
    workflow.add_conditional_edges(
        "execute",
        route_after_execute,
        {"reflect": "reflect", "end": END},
    )
    workflow.add_conditional_edges(
        "reflect",
        route_after_reflection,
        {"generate": "generate", "retrieve": "retrieve", "end": END},
    )

    workflow.set_entry_point("analyze")

    return workflow.compile()

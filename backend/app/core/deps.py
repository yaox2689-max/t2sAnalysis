"""Application context — global dependencies with lazy initialisation.

Initialises on first request:
1. Bootstrap (DuckDB + Registry + PromptBuilder + Executor)
2. LLM clients (TaskAnalyzer, SQLGenerator, ReflectionLoop)
3. LangGraph Workflow
4. ChartTool + InsightTool

Usage:
    from app.core.deps import app_ctx

    ctx = await app_ctx.ensure_initialized()
    result = await ctx.graph.ainvoke({...})
"""

import asyncio
import logging
from typing import Optional

from langgraph.graph.state import CompiledStateGraph

from app.core.config import settings
from app.core.database import Database
from app.tools.chart import ChartTool
from app.tools.insight import InsightTool

logger = logging.getLogger("t2s_analysis")


class AppContext:
    """Holds all application-level dependencies."""

    def __init__(self) -> None:
        self.graph: Optional[CompiledStateGraph] = None
        self.chart_tool: Optional[ChartTool] = None
        self.insight_tool: Optional[InsightTool] = None
        self._initialized: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()

    async def ensure_initialized(self) -> "AppContext":
        """Lazy-init all dependencies on first call (thread-safe)."""
        if self._initialized:
            return self

        async with self._lock:
            if self._initialized:
                return self

            logger.info({"event": "app_init_start"})

            # 1. Bootstrap (DuckDB + Registry + PromptBuilder + Executor)
            from app.bootstrap import bootstrap
            await bootstrap.run()

            # 2. MySQL (business metadata only — sessions, messages)
            from app.core.database import db
            db.init()

            # 3. LLM client config
            api_key = settings.LLM_API_KEY
            model = settings.LLM_MODEL
            base_url = settings.LLM_BASE_URL

            if not api_key:
                logger.warning({"event": "llm_api_key_missing"})

            # 4. Task Analyzer
            from app.services.task_analyzer import TaskAnalyzer
            analyzer = TaskAnalyzer(api_key=api_key, model=model, base_url=base_url)

            # 5. SQL Generator
            from app.agents.sql_generator import SQLGenerator
            generator = SQLGenerator(api_key=api_key, model=model, base_url=base_url)

            # 6. Validator
            from app.tools.sql_validator import SQLValidator
            validator = SQLValidator()

            # 7. Executor (DuckDB)
            executor = bootstrap.executor

            # 8. Reflection
            from app.agents.reflection import ReflectionLoop
            # Reflection needs a retriever for schema_error re-retrieval
            # Use a minimal adapter that wraps the registry
            retriever_adapter = _RegistryRetrieverAdapter(bootstrap.registry)
            reflection = ReflectionLoop(
                api_key=api_key, model=model, base_url=base_url,
                sql_generator=generator, schema_retriever=retriever_adapter,
            )

            # 9. Build the Workflow graph (new path: registry + prompt_builder)
            from app.graph.graph import build_graph
            self.graph = build_graph(
                analyzer=analyzer,
                registry=bootstrap.registry,
                prompt_builder=bootstrap.prompt_builder,
                generator=generator,
                validator=validator,
                executor=executor,
                reflection=reflection,
            )

            # 10. Tools
            self.chart_tool = ChartTool()
            self.insight_tool = InsightTool(api_key=api_key, model=model, base_url=base_url)

            self._initialized = True
            logger.info({"event": "app_init_complete"})
            return self


class _RegistryRetrieverAdapter:
    """Adapter that wraps DatasetRegistry to look like a SchemaRetriever.

    Used by ReflectionLoop for schema_error re-retrieval.
    The reflection loop calls retriever.retrieve(question) when it
    detects a schema error, and this adapter makes that work with
    the new registry.
    """

    def __init__(self, registry: object) -> None:
        self._registry = registry

    async def retrieve(self, question: str, **kwargs) -> object:
        """Re-retrieve schema context using the registry."""
        from app.models.task import SchemaContext

        catalog = self._registry.get_catalog(question=question, top_k=10)
        return SchemaContext(
            tables=[t.table_name for t in catalog.tables],
            columns={
                t.table_name: [{"column_name": c.name, "data_type": c.data_type} for c in t.columns]
                for t in catalog.tables
            },
        )


# Module-level singleton
app_ctx = AppContext()

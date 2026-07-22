"""Application context — global dependencies with lazy initialisation.

Initialises on first request:
1. Database connection pool
2. SchemaIndex (FAISS)
3. LangGraph Workflow with all node modules
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

            # 1. Database
            from app.core.database import db
            db.init()

            # 2. Schema Repository
            from app.repositories.schema_repository import SchemaRepository
            repo = SchemaRepository()

            # 3. Embedding provider (dummy for now — real embedding uses OpenAI)
            from app.schemas.embedding import EmbeddingProvider

            class _DummyEmbed(EmbeddingProvider):
                async def embed(self, texts: list[str]) -> list[list[float]]:
                    dim = 384
                    return [[0.01] * dim for _ in texts]

            embed_provider = _DummyEmbed()

            # 4. Schema Index
            from app.schemas.schema_index import SchemaIndex
            index = SchemaIndex(repo, embed_provider)
            try:
                await index.build()
                logger.info({"event": "schema_index_built"})
            except Exception as exc:
                logger.error({"event": "schema_index_build_failed", "error": str(exc)})

            # 5. Schema Retriever
            from app.schemas.schema_retriever import SchemaRetriever
            retriever = SchemaRetriever(index, repo)

            # 6. LLM client config
            api_key = settings.LLM_API_KEY
            model = settings.LLM_MODEL
            base_url = settings.LLM_BASE_URL

            if not api_key:
                logger.warning({"event": "llm_api_key_missing"})

            # 7. Task Analyzer
            from app.services.task_analyzer import TaskAnalyzer
            analyzer = TaskAnalyzer(api_key=api_key, model=model, base_url=base_url)

            # 8. SQL Generator
            from app.agents.sql_generator import SQLGenerator
            generator = SQLGenerator(api_key=api_key, model=model, base_url=base_url)

            # 9. Validator
            from app.tools.sql_validator import SQLValidator
            validator = SQLValidator()

            # 10. Executor
            from app.tools.sql_executor import SafeExecutor
            executor = SafeExecutor()

            # 11. Reflection
            from app.agents.reflection import ReflectionLoop
            reflection = ReflectionLoop(
                api_key=api_key, model=model, base_url=base_url,
                sql_generator=generator, schema_retriever=retriever,
            )

            # 12. Build the Workflow graph
            from app.graph.graph import build_graph
            self.graph = build_graph(
                analyzer=analyzer,
                retriever=retriever,
                generator=generator,
                validator=validator,
                executor=executor,
                reflection=reflection,
            )

            # 13. Tools
            self.chart_tool = ChartTool()
            self.insight_tool = InsightTool(api_key=api_key, model=model, base_url=base_url)

            self._initialized = True
            logger.info({"event": "app_init_complete"})
            return self


# Global singleton
app_ctx = AppContext()

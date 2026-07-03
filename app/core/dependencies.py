from app.catalog.data_catalog import DataCatalog
from app.compiler.analytical_planner import AnalyticalPlanner
from app.compiler.compiler import TerbieCompiler
from app.compiler.execution_plan_builder import ExecutionPlanBuilder
from app.compiler.hypothesis_builder import HypothesisBuilder
from app.core.config import Settings, get_settings
from app.datasources.factory import DataSourceFactory
from app.datasources.google_sheets import GoogleSheetsDataSource
from app.datasources.registry import DataSourceRegistry
from app.entity_resolution.entity_resolver import EntityResolver
from app.executor.engine import PandasExecutionEngine
from app.executor.executor import TerbieExecutor
from app.executor.pipeline import PipelineExecutor
from app.executor.registry import OperationRegistry
from app.intent_guard.intent_guard import IntentGuard
from app.knowledge.knowledge_service import KnowledgeService
from app.narrator.context_builder import NarrativeContextBuilder
from app.narrator.formatter import NarrativeFormatter
from app.narrator.narrator import TerbieNarrator
from app.orchestrator.terbie_orchestrator import TerbieOrchestrator
from app.planner.compiler import PlannerCompiler
from app.planner.context_composer import PlannerContextComposer
from app.planner.optimizer import PlanOptimizer
from app.planner.parser import PlanParser
from app.planner.planner import QueryPlanner
from app.planner.validator import PlanValidator
from app.query_plan.builder import LogicalQueryPlanBuilder
from app.query_plan.validator import LogicalQueryPlanValidator
from app.reasoning.base import BaseReasoningProvider
from app.reasoning.factory import ReasoningProviderFactory
from app.schemas.discovery import SchemaDiscovery
from app.semantic.resolver import SemanticResolver
from app.services.data_service import DataService
from app.services.execution_service import ExecutionService
from app.services.health_service import HealthService
from app.services.narrator_service import NarratorService
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService

_data_catalog = DataCatalog()
_semantic_resolver = SemanticResolver()
_datasource_registry: DataSourceRegistry | None = None


def provide_settings() -> Settings:
    return get_settings()


def provide_health_service() -> HealthService:
    return HealthService(settings=provide_settings())


def provide_data_catalog() -> DataCatalog:
    return _data_catalog


def provide_google_sheets_data_source() -> GoogleSheetsDataSource:
    return GoogleSheetsDataSource(settings=provide_settings())


def provide_datasource_registry() -> DataSourceRegistry:
    global _datasource_registry

    if _datasource_registry is None:
        _datasource_registry = DataSourceFactory().create_registry(settings=provide_settings())

    return _datasource_registry


def provide_schema_discovery() -> SchemaDiscovery:
    return SchemaDiscovery()


def provide_data_service() -> DataService:
    return DataService(
        datasource_registry=provide_datasource_registry(),
        schema_discovery=provide_schema_discovery(),
        data_catalog=provide_data_catalog(),
        default_datasource=provide_settings().default_datasource,
        default_table=provide_settings().default_table,
        blocked_tables=provide_settings().blocked_tables,
    )


def provide_knowledge_service() -> KnowledgeService:
    return KnowledgeService()


def provide_semantic_resolver() -> SemanticResolver:
    return _semantic_resolver


def provide_semantic_service() -> SemanticService:
    return SemanticService(resolver=provide_semantic_resolver())


def provide_intent_guard() -> IntentGuard:
    return IntentGuard()


def provide_entity_resolver() -> EntityResolver:
    return EntityResolver()


def provide_query_planner() -> QueryPlanner:
    return QueryPlanner()


def provide_plan_validator() -> PlanValidator:
    return PlanValidator()


def provide_plan_optimizer() -> PlanOptimizer:
    return PlanOptimizer()


def provide_plan_parser() -> PlanParser:
    return PlanParser()


def provide_logical_query_plan_builder() -> LogicalQueryPlanBuilder:
    return LogicalQueryPlanBuilder()


def provide_logical_query_plan_validator() -> LogicalQueryPlanValidator:
    return LogicalQueryPlanValidator()


def provide_planner_context_composer() -> PlannerContextComposer:
    return PlannerContextComposer()


def provide_reasoning_provider() -> BaseReasoningProvider:
    return ReasoningProviderFactory().create(settings=provide_settings())


def provide_planner_compiler() -> PlannerCompiler:
    return PlannerCompiler(
        context_composer=provide_planner_context_composer(),
        reasoning_provider=provide_reasoning_provider(),
        parser=provide_plan_parser(),
        validator=provide_plan_validator(),
        optimizer=provide_plan_optimizer(),
    )


def provide_hypothesis_builder() -> HypothesisBuilder:
    return HypothesisBuilder()


def provide_analytical_planner() -> AnalyticalPlanner:
    return AnalyticalPlanner()


def provide_execution_plan_builder() -> ExecutionPlanBuilder:
    return ExecutionPlanBuilder()


def provide_terbie_compiler() -> TerbieCompiler:
    return TerbieCompiler(
        hypothesis_builder=provide_hypothesis_builder(),
        analytical_planner=provide_analytical_planner(),
        execution_plan_builder=provide_execution_plan_builder(),
        validator=provide_plan_validator(),
        optimizer=provide_plan_optimizer(),
        reasoning_provider=provide_reasoning_provider(),
        entity_resolver=provide_entity_resolver(),
    )


def provide_planner_service() -> PlannerService:
    return PlannerService(compiler=provide_terbie_compiler())


def provide_operation_registry() -> OperationRegistry:
    return OperationRegistry()


def provide_pipeline_executor() -> PipelineExecutor:
    return PipelineExecutor(registry=provide_operation_registry())


def provide_pandas_execution_engine() -> PandasExecutionEngine:
    return PandasExecutionEngine(pipeline_executor=provide_pipeline_executor())


def provide_terbie_executor() -> TerbieExecutor:
    return TerbieExecutor(engine=provide_pandas_execution_engine())


def provide_narrative_context_builder() -> NarrativeContextBuilder:
    return NarrativeContextBuilder()


def provide_narrative_formatter() -> NarrativeFormatter:
    return NarrativeFormatter()


def provide_terbie_narrator() -> TerbieNarrator:
    return TerbieNarrator(
        context_builder=provide_narrative_context_builder(),
        formatter=provide_narrative_formatter(),
    )


def provide_narrator_service() -> NarratorService:
    return NarratorService(narrator=provide_terbie_narrator())


def provide_execution_service() -> ExecutionService:
    return ExecutionService(
        settings=provide_settings(),
        semantic_service=provide_semantic_service(),
        planner_service=provide_planner_service(),
        data_service=provide_data_service(),
        executor=provide_terbie_executor(),
        narrator_service=provide_narrator_service(),
        intent_guard=provide_intent_guard(),
    )


def provide_terbie_orchestrator() -> TerbieOrchestrator:
    return TerbieOrchestrator(
        semantic_service=provide_semantic_service(),
        planner_service=provide_planner_service(),
        knowledge_service=provide_knowledge_service(),
        intent_guard=provide_intent_guard(),
    )

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.catalog.data_catalog import DataCatalog
from app.compiler.models import CompilerResponse
from app.core.config import Settings
from app.core.dependencies import (
    provide_data_catalog,
    provide_data_service,
    provide_execution_service,
    provide_health_service,
    provide_knowledge_service,
    provide_narrator_service,
    provide_planner_service,
    provide_semantic_service,
    provide_settings,
    provide_terbie_orchestrator,
)
from app.datasources.models import DataSourceHealth, DataSourceInfo
from app.executor.models import ExecutionRequest
from app.knowledge.knowledge_service import KnowledgeService
from app.knowledge.models import (
    BusinessDimension,
    BusinessEntity,
    BusinessMetric,
    BusinessRule,
    KnowledgeContext,
)
from app.models.data_source import GoogleSheetsLoadRequest
from app.models.health import HealthResponse
from app.models.schema import TableSchema
from app.narrator.models import ExecuteResponse, NarratorRequest, NarratorResponse
from app.orchestrator.terbie_orchestrator import TerbieDraftResponse, TerbieOrchestrator
from app.planner.models import PlannerRequest, PlannerResponse
from app.semantic.models import SemanticResolutionRequest, SemanticResolutionResponse
from app.services.data_service import DataService
from app.services.execution_service import ExecutionService
from app.services.health_service import HealthService
from app.services.narrator_service import NarratorService
from app.services.planner_service import PlannerService
from app.services.semantic_service import SemanticService

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check(
    health_service: Annotated[HealthService, Depends(provide_health_service)],
) -> HealthResponse:
    return health_service.get_health()


@router.get("/tables", response_model=list[str], tags=["catalog"])
def list_tables(
    data_catalog: Annotated[DataCatalog, Depends(provide_data_catalog)],
) -> list[str]:
    return data_catalog.list_tables()


@router.get("/schema/{table}", response_model=TableSchema, tags=["catalog"])
def get_table_schema(
    table: str,
    data_catalog: Annotated[DataCatalog, Depends(provide_data_catalog)],
) -> TableSchema:
    schema = data_catalog.get_schema(table)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"Table '{table}' not found")

    return schema


@router.get("/datasources", response_model=list[DataSourceInfo], tags=["datasources"])
def list_datasources(
    data_service: Annotated[DataService, Depends(provide_data_service)],
) -> list[DataSourceInfo]:
    return data_service.list_datasources()


@router.get("/datasources/health", response_model=list[DataSourceHealth], tags=["datasources"])
def get_datasources_health(
    data_service: Annotated[DataService, Depends(provide_data_service)],
) -> list[DataSourceHealth]:
    return data_service.check_datasource_health()


@router.get(
    "/datasources/{datasource_name}/tables",
    response_model=list[str],
    tags=["datasources"],
)
def list_datasource_tables(
    datasource_name: str,
    data_service: Annotated[DataService, Depends(provide_data_service)],
) -> list[str]:
    return data_service.list_tables(datasource_name=datasource_name)


@router.get(
    "/datasources/{datasource_name}/schema/{table_name}",
    response_model=TableSchema,
    tags=["datasources"],
)
def get_datasource_table_schema(
    datasource_name: str,
    table_name: str,
    data_service: Annotated[DataService, Depends(provide_data_service)],
) -> TableSchema:
    return data_service.get_table_schema(
        datasource_name=datasource_name,
        table_name=table_name,
    )


@router.get("/knowledge/context", response_model=KnowledgeContext, tags=["knowledge"])
def get_knowledge_context(
    knowledge_service: Annotated[KnowledgeService, Depends(provide_knowledge_service)],
) -> KnowledgeContext:
    return knowledge_service.get_context()


@router.get("/knowledge/metrics", response_model=list[BusinessMetric], tags=["knowledge"])
def get_knowledge_metrics(
    knowledge_service: Annotated[KnowledgeService, Depends(provide_knowledge_service)],
) -> list[BusinessMetric]:
    return knowledge_service.get_metrics()


@router.get("/knowledge/dimensions", response_model=list[BusinessDimension], tags=["knowledge"])
def get_knowledge_dimensions(
    knowledge_service: Annotated[KnowledgeService, Depends(provide_knowledge_service)],
) -> list[BusinessDimension]:
    return knowledge_service.get_dimensions()


@router.get("/knowledge/rules", response_model=list[BusinessRule], tags=["knowledge"])
def get_knowledge_rules(
    knowledge_service: Annotated[KnowledgeService, Depends(provide_knowledge_service)],
) -> list[BusinessRule]:
    return knowledge_service.get_rules()


@router.get("/knowledge/entities", response_model=list[BusinessEntity], tags=["knowledge"])
def get_knowledge_entities(
    knowledge_service: Annotated[KnowledgeService, Depends(provide_knowledge_service)],
) -> list[BusinessEntity]:
    return knowledge_service.get_entities()


@router.post("/sources/google-sheets/load", response_model=list[TableSchema], tags=["datasources"])
def load_google_sheets(
    payload: GoogleSheetsLoadRequest,
    data_service: Annotated[DataService, Depends(provide_data_service)],
    settings: Annotated[Settings, Depends(provide_settings)],
) -> list[TableSchema]:
    spreadsheet_id = payload.spreadsheet_id or settings.google_sheets_spreadsheet_id
    if spreadsheet_id is None or spreadsheet_id.strip() == "":
        raise HTTPException(
            status_code=400,
            detail=(
                "Spreadsheet ID is required. "
                "Set GOOGLE_SHEETS_SPREADSHEET_ID or send spreadsheet_id."
            ),
        )

    return data_service.load_google_spreadsheet(
        spreadsheet_id=spreadsheet_id,
        sheet_names=payload.sheet_names,
    )


@router.post(
    "/semantic/resolve",
    response_model=SemanticResolutionResponse,
    tags=["semantic"],
)
def resolve_semantic_query(
    payload: SemanticResolutionRequest,
    semantic_service: Annotated[SemanticService, Depends(provide_semantic_service)],
) -> SemanticResolutionResponse:
    return SemanticResolutionResponse(
        resolution=semantic_service.resolve(question=payload.question),
    )


@router.post(
    "/planner/draft",
    response_model=PlannerResponse,
    tags=["planner"],
)
def create_draft_plan(
    payload: PlannerRequest,
    knowledge_service: Annotated[KnowledgeService, Depends(provide_knowledge_service)],
    semantic_service: Annotated[SemanticService, Depends(provide_semantic_service)],
    planner_service: Annotated[PlannerService, Depends(provide_planner_service)],
) -> PlannerResponse:
    semantic_resolution = semantic_service.resolve(question=payload.question)
    return planner_service.create_draft_plan(
        question=payload.question,
        semantic_resolution=semantic_resolution,
        knowledge_context=knowledge_service.get_context(),
    )


@router.post(
    "/compiler/draft",
    response_model=CompilerResponse,
    tags=["compiler"],
)
def create_compiler_draft(
    payload: PlannerRequest,
    knowledge_service: Annotated[KnowledgeService, Depends(provide_knowledge_service)],
    semantic_service: Annotated[SemanticService, Depends(provide_semantic_service)],
    planner_service: Annotated[PlannerService, Depends(provide_planner_service)],
) -> CompilerResponse:
    semantic_resolution = semantic_service.resolve(question=payload.question)
    return planner_service.create_compiler_draft(
        question=payload.question,
        semantic_resolution=semantic_resolution,
        knowledge_context=knowledge_service.get_context(),
    )


@router.post("/execute", response_model=ExecuteResponse, tags=["executor"])
def execute_question(
    payload: ExecutionRequest,
    execution_service: Annotated[ExecutionService, Depends(provide_execution_service)],
    knowledge_service: Annotated[KnowledgeService, Depends(provide_knowledge_service)],
) -> ExecuteResponse:
    return execution_service.execute_question(
        question=payload.question,
        knowledge_context=knowledge_service.get_context(),
    )


@router.post("/narrator/draft", response_model=NarratorResponse, tags=["narrator"])
def create_narrator_draft(
    payload: NarratorRequest,
    narrator_service: Annotated[NarratorService, Depends(provide_narrator_service)],
) -> NarratorResponse:
    return narrator_service.narrate(payload)


@router.post(
    "/ask/draft",
    response_model=TerbieDraftResponse,
    tags=["orchestrator"],
)
def create_orchestrated_draft(
    payload: PlannerRequest,
    orchestrator: Annotated[TerbieOrchestrator, Depends(provide_terbie_orchestrator)],
) -> TerbieDraftResponse:
    return orchestrator.create_draft(question=payload.question)

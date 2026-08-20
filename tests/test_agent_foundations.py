from pathlib import Path

import pandas as pd

from app.catalog.data_catalog import DataCatalog
from app.agents.analytical_agent import AnalyticalAgent
from app.executor.context import ExecutionContext
from app.executor.models import ExecutionResult
from app.executor.operations.filter_group import FilterGroupOperation
from app.executor.operations.statistics import StatisticsOperation
from app.executor.pipeline import PipelineExecutor
from app.executor.registry import OperationRegistry
from app.governance.policy import DataGovernancePolicy
from app.knowledge.knowledge_service import KnowledgeService
from app.memory.sqlite import SQLiteSessionStore
from app.models.schema import ColumnSchema, DataCatalogEntry, TableSchema
from app.planner.models import ExecutionPlan, PlanOperation
from app.services.analysis_verifier import AnalysisVerifier


def _context() -> ExecutionContext:
    return ExecutionContext(knowledge_context=KnowledgeService().get_context())


def test_nested_filter_groups_support_or_of_and_clauses() -> None:
    dataframe = pd.DataFrame(
        {
            "campanha": ["A", "A", "B"],
            "shopping": ["X", "Y", "Y"],
            "valor": [1, 2, 3],
        },
    )
    expression = {
        "logical": "or",
        "clauses": [
            {
                "logical": "and",
                "clauses": [
                    {"field": "campanha", "operator": "equals", "value": "A"},
                    {"field": "shopping", "operator": "equals", "value": "X"},
                ],
            },
            {
                "logical": "and",
                "clauses": [
                    {"field": "campanha", "operator": "equals", "value": "B"},
                    {"field": "shopping", "operator": "equals", "value": "Y"},
                ],
            },
        ],
    }

    result = FilterGroupOperation().execute(
        dataframe,
        PlanOperation(type="filter_group", parameters={"expression": expression}),
        _context(),
    )

    assert result["valor"].tolist() == [1, 3]


def test_statistics_operation_calculates_descriptive_profile() -> None:
    result = StatisticsOperation().execute(
        pd.DataFrame({"valor": [1, 2, 3, 4]}),
        PlanOperation(type="statistics", function="describe", field="valor"),
        _context(),
    )

    assert result.iloc[0]["media"] == 2.5
    assert result.iloc[0]["mediana"] == 2.5


def test_pipeline_records_row_count_and_duration_for_each_operation() -> None:
    result = PipelineExecutor(OperationRegistry()).execute(
        dataframe=pd.DataFrame({"grupo": ["A", "B"], "valor": [1, 2]}),
        plan=ExecutionPlan(
            entities=[],
            metrics=[],
            operations=[PlanOperation(type="filter", field="grupo", parameters={"value": "A"})],
        ),
        context=_context(),
    )

    assert result.metadata["operation_trace"][0]["rows_before"] == 2
    assert result.metadata["operation_trace"][0]["rows_after"] == 1


def test_verifier_rejects_invalid_percentage() -> None:
    result = ExecutionResult(
        data=[{"percentual_genero": 1.2}],
        metadata={"operation_trace": []},
        statistics={},
        warnings=[],
        execution_time=0,
        rows_returned=1,
    )

    verification = AnalysisVerifier().verify(plan=ExecutionPlan(), result=result)

    assert verification.passed is False
    assert verification.checks["percentages_valid"] is False


def test_governance_masks_pii_and_suppresses_small_groups() -> None:
    rows = [
        {"grupo": "A", "clientes_unicos": 2, "cpf": "123"},
        {"grupo": "B", "clientes_unicos": 5, "email_cliente": "x@example.com"},
    ]

    result = DataGovernancePolicy(minimum_group_size=3).sanitize(rows)

    assert result == [{"grupo": "B", "clientes_unicos": 5}]


def test_governance_suppresses_a_single_small_group_and_limits_shopping_scope() -> None:
    policy = DataGovernancePolicy(
        minimum_group_size=3,
        allowed_shoppings={"Shopping Sul"},
    )

    assert policy.sanitize(
        [{"nm_empreendimento": "Shopping Sul", "clientes_unicos": 2}],
    ) == []
    assert policy.sanitize(
        [{"nm_empreendimento": "Outro Shopping", "clientes_unicos": 10}],
    ) == []


def test_sqlite_memory_persists_between_store_instances(tmp_path: Path) -> None:
    path = str(tmp_path / "memory.db")
    SQLiteSessionStore(path).save("session", {"value": 1})

    assert SQLiteSessionStore(path).load("session") == {"value": 1}


def test_catalog_selects_table_that_contains_required_columns() -> None:
    catalog = DataCatalog()
    for name, columns, rows in (
        ("small", ["a"], 10),
        ("complete", ["a", "b"], 20),
    ):
        catalog.register_table(
            DataCatalogEntry(
                table_name=name,
                source="test",
                table_schema=TableSchema(
                    name=name,
                    row_count=rows,
                    columns=[
                        ColumnSchema(
                            name=column,
                            data_type="string",
                            nullable=False,
                            null_count=0,
                            unique_count=1,
                        )
                        for column in columns
                    ],
                ),
            ),
        )

    assert catalog.best_table_for_columns({"a", "b"}) == "complete"


def test_catalog_schema_and_dimension_index_are_persisted(tmp_path: Path) -> None:
    catalog = DataCatalog()
    catalog.register_table(
        DataCatalogEntry(
            table_name="vendas",
            source="test",
            table_schema=TableSchema(name="vendas", row_count=0, columns=[]),
        ),
    )
    catalog.register_dimension_values(
        table_name="vendas",
        column="shopping",
        values=["Shopping A"],
    )
    path = str(tmp_path / "catalog.json")
    catalog.persist(path)

    restored = DataCatalog()

    assert restored.restore(path) is True
    assert restored.list_tables() == ["vendas"]
    assert restored.dimension_values(table_name="vendas", column="shopping") == [
        "Shopping A",
    ]


def test_analytical_agent_repairs_once_after_failed_verification() -> None:
    initial = ExecutionPlan(intent="persona")
    repaired = ExecutionPlan(intent="persona", version="2.0")
    executed_versions: list[str] = []

    def execute(plan: ExecutionPlan) -> ExecutionResult:
        executed_versions.append(plan.version)
        percentage = 1.2 if plan.version == "1.0" else 0.8
        return ExecutionResult(
            data=[{"percentual_genero": percentage}],
            metadata={"operation_trace": []},
            statistics={},
            warnings=[],
            execution_time=0,
            rows_returned=1,
        )

    result = AnalyticalAgent(max_repairs=1).run(
        plan=initial,
        execute=execute,
        repair=lambda plan, verification: repaired,
    )

    assert result.verification.passed is True
    assert result.attempts == 2
    assert executed_versions == ["1.0", "2.0"]

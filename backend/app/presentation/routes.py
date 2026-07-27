import io
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.domain.dataset.entity import Dataset
from app.domain.dataset.errors import FileTooLargeError
from app.domain.dataset.values import Aggregation, ExportFormat, FilterSpec, SortSpec, TimeFrequency
from app.presentation.container import Container, get_container
from app.presentation.schemas import (
    DatasetMetaSchema,
    ExportRequest,
    FilterSchema,
    GroupRowSchema,
    InsightSchema,
    NumericSummarySchema,
    OverviewSchema,
    PageSchema,
    QueryRequest,
    SortSchema,
    TimePointSchema,
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_READ_CHUNK = 1024 * 1024

ContainerDep = Annotated[Container, Depends(get_container)]

_MEDIA_TYPES = {
    ExportFormat.CSV: "text/csv; charset=utf-8",
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _meta(dataset: Dataset) -> DatasetMetaSchema:
    return DatasetMetaSchema(
        id=dataset.id,
        name=dataset.name,
        uploaded_at=dataset.uploaded_at,
        row_count=dataset.table.row_count(),
        column_count=dataset.table.column_count(),
    )


def _filters(schemas: list[FilterSchema]) -> list[FilterSpec]:
    return [FilterSpec(column=f.column, operator=f.operator, value=f.value) for f in schemas]


def _sort(schemas: list[SortSchema]) -> list[SortSpec]:
    return [SortSpec(column=s.column, descending=s.descending) for s in schemas]


def _file_response(content: bytes, filename: str, media_type: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.post("", response_model=DatasetMetaSchema)
async def upload_dataset(file: UploadFile, container: ContainerDep) -> DatasetMetaSchema:
    content = bytearray()
    while chunk := await file.read(_READ_CHUNK):
        content.extend(chunk)
        if len(content) > MAX_UPLOAD_BYTES:
            raise FileTooLargeError(MAX_UPLOAD_BYTES)
    dataset = await run_in_threadpool(
        container.upload_dataset.execute, file.filename or "dataset", bytes(content)
    )
    return _meta(dataset)


@router.get("", response_model=list[DatasetMetaSchema])
def list_datasets(container: ContainerDep) -> list[DatasetMetaSchema]:
    return [_meta(d) for d in container.list_datasets.execute()]


@router.get("/{dataset_id}", response_model=OverviewSchema)
def get_overview(dataset_id: str, container: ContainerDep) -> OverviewSchema:
    dataset, overview = container.get_overview.execute(dataset_id)
    return OverviewSchema(
        dataset=_meta(dataset),
        columns=overview.columns,
        preview=overview.preview,
    )


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str, container: ContainerDep) -> None:
    container.delete_dataset.execute(dataset_id)


@router.post("/{dataset_id}/query", response_model=PageSchema)
def query_rows(dataset_id: str, body: QueryRequest, container: ContainerDep) -> PageSchema:
    page = container.query_rows.execute(
        dataset_id,
        filters=_filters(body.filters),
        sort=_sort(body.sort),
        page=body.page,
        page_size=body.page_size,
    )
    return PageSchema.model_validate(page)


@router.get("/{dataset_id}/summary", response_model=list[NumericSummarySchema])
def get_summary(dataset_id: str, container: ContainerDep) -> list[NumericSummarySchema]:
    return [NumericSummarySchema.model_validate(s) for s in container.get_summary.execute(dataset_id)]


@router.get("/{dataset_id}/top", response_model=PageSchema)
def get_top_values(
    dataset_id: str,
    container: ContainerDep,
    metric: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    ascending: bool = False,
) -> PageSchema:
    page = container.get_top_values.execute(
        dataset_id, metric=metric, limit=limit, ascending=ascending, filters=[]
    )
    return PageSchema.model_validate(page)


@router.get("/{dataset_id}/group-by", response_model=list[GroupRowSchema])
def get_group_breakdown(
    dataset_id: str,
    container: ContainerDep,
    by: str,
    metric: str | None = None,
    aggregation: Aggregation = Aggregation.SUM,
) -> list[GroupRowSchema]:
    rows = container.get_group_breakdown.execute(
        dataset_id, by=by, metric=metric, aggregation=aggregation, filters=[]
    )
    return [GroupRowSchema.model_validate(r) for r in rows]


@router.get("/{dataset_id}/time-series", response_model=list[TimePointSchema])
def get_time_series(
    dataset_id: str,
    container: ContainerDep,
    date_column: Annotated[str, Query(alias="dateColumn")],
    metric: str | None = None,
    aggregation: Aggregation = Aggregation.SUM,
    frequency: TimeFrequency = TimeFrequency.DAY,
) -> list[TimePointSchema]:
    points = container.get_time_series.execute(
        dataset_id,
        date_column=date_column,
        metric=metric,
        aggregation=aggregation,
        frequency=frequency,
        filters=[],
    )
    return [TimePointSchema.model_validate(p) for p in points]


@router.get("/{dataset_id}/insights", response_model=list[InsightSchema])
def get_insights(dataset_id: str, container: ContainerDep) -> list[InsightSchema]:
    return [InsightSchema.model_validate(i) for i in container.generate_insights.execute(dataset_id)]


@router.post("/{dataset_id}/export")
def export_rows(dataset_id: str, body: ExportRequest, container: ContainerDep) -> StreamingResponse:
    content, filename = container.export_rows.execute(
        dataset_id,
        filters=_filters(body.filters),
        sort=_sort(body.sort),
        fmt=body.format,
    )
    return _file_response(content, filename, _MEDIA_TYPES[body.format])


@router.get("/{dataset_id}/report")
def export_report(dataset_id: str, container: ContainerDep) -> StreamingResponse:
    content, filename = container.export_report.execute(dataset_id)
    return _file_response(content, filename, _MEDIA_TYPES[ExportFormat.XLSX])

from dataclasses import dataclass
from functools import lru_cache

from app.application.usecases.dataset.delete_dataset import DeleteDataset
from app.application.usecases.dataset.export_report import ExportReport
from app.application.usecases.dataset.export_rows import ExportRows
from app.application.usecases.dataset.generate_insights import GenerateInsights
from app.application.usecases.dataset.get_group_breakdown import GetGroupBreakdown
from app.application.usecases.dataset.get_overview import GetOverview
from app.application.usecases.dataset.get_summary import GetSummary
from app.application.usecases.dataset.get_time_series import GetTimeSeries
from app.application.usecases.dataset.get_top_values import GetTopValues
from app.application.usecases.dataset.list_datasets import ListDatasets
from app.application.usecases.dataset.query_rows import QueryRows
from app.application.usecases.dataset.upload_dataset import UploadDataset
from app.infrastructure.dataframe.parser import PandasDatasetParser
from app.infrastructure.persistence.in_memory_repository import InMemoryDatasetRepository
from app.infrastructure.reporting.xlsx_report import XlsxReportBuilder


@dataclass(frozen=True)
class Container:
    upload_dataset: UploadDataset
    list_datasets: ListDatasets
    get_overview: GetOverview
    delete_dataset: DeleteDataset
    query_rows: QueryRows
    get_summary: GetSummary
    get_top_values: GetTopValues
    get_group_breakdown: GetGroupBreakdown
    get_time_series: GetTimeSeries
    generate_insights: GenerateInsights
    export_rows: ExportRows
    export_report: ExportReport


@lru_cache(maxsize=1)
def get_container() -> Container:
    repository = InMemoryDatasetRepository()
    parser = PandasDatasetParser()
    report_builder = XlsxReportBuilder()
    insights = GenerateInsights(repository)
    return Container(
        upload_dataset=UploadDataset(repository, parser),
        list_datasets=ListDatasets(repository),
        get_overview=GetOverview(repository),
        delete_dataset=DeleteDataset(repository),
        query_rows=QueryRows(repository),
        get_summary=GetSummary(repository),
        get_top_values=GetTopValues(repository),
        get_group_breakdown=GetGroupBreakdown(repository),
        get_time_series=GetTimeSeries(repository),
        generate_insights=insights,
        export_rows=ExportRows(repository),
        export_report=ExportReport(repository, report_builder, insights),
    )

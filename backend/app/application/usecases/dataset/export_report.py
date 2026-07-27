from app.application.ports import ReportBuilder
from app.application.usecases.dataset.generate_insights import GenerateInsights
from app.domain.dataset.repository import DatasetRepository


class ExportReport:
    def __init__(
        self,
        repository: DatasetRepository,
        report_builder: ReportBuilder,
        generate_insights: GenerateInsights,
    ) -> None:
        self._repository = repository
        self._report_builder = report_builder
        self._generate_insights = generate_insights

    def execute(self, dataset_id: str) -> tuple[bytes, str]:
        dataset = self._repository.get(dataset_id)
        insights = self._generate_insights.execute(dataset_id)
        content = self._report_builder.build(dataset, insights)
        stem = dataset.name.rsplit(".", 1)[0]
        return content, f"{stem}_report.xlsx"

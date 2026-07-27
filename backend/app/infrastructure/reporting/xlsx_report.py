import io

import pandas as pd

from app.domain.dataset.entity import Dataset
from app.domain.dataset.results import Insight


class XlsxReportBuilder:
    def build(self, dataset: Dataset, insights: list[Insight]) -> bytes:
        table = dataset.table
        overview = pd.DataFrame(
            {
                "Параметр": ["Файл", "Загружен", "Строк", "Колонок"],
                "Значение": [
                    dataset.name,
                    dataset.uploaded_at.strftime("%Y-%m-%d %H:%M UTC"),
                    table.row_count(),
                    table.column_count(),
                ],
            }
        )
        columns = pd.DataFrame(
            [
                {
                    "Колонка": c.name,
                    "Тип": c.dtype,
                    "Категория": c.kind.value,
                    "Пропуски": c.missing,
                    "Уникальных": c.unique,
                }
                for c in table.columns()
            ]
        )
        summary = pd.DataFrame(
            [
                {
                    "Колонка": s.column,
                    "Count": s.count,
                    "Mean": s.mean,
                    "Std": s.std,
                    "Min": s.minimum,
                    "P25": s.p25,
                    "Median": s.median,
                    "P75": s.p75,
                    "Max": s.maximum,
                }
                for s in table.summary()
            ]
        )
        insight_rows = pd.DataFrame(
            [{"Инсайт": i.title, "Описание": i.detail} for i in insights]
        )
        data = pd.DataFrame(table.rows(filters=[], sort=[], page=1, page_size=10_000).rows)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            overview.to_excel(writer, index=False, sheet_name="Обзор")
            columns.to_excel(writer, index=False, sheet_name="Колонки")
            if not summary.empty:
                summary.to_excel(writer, index=False, sheet_name="Статистика")
            if not insight_rows.empty:
                insight_rows.to_excel(writer, index=False, sheet_name="Инсайты")
            data.to_excel(writer, index=False, sheet_name="Данные")
        return buffer.getvalue()

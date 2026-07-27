from app.domain.dataset.repository import DatasetRepository
from app.domain.dataset.results import Insight
from app.domain.dataset.table import DataTable
from app.domain.dataset.values import Aggregation, ColumnKind


def _fmt_pct(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def _fmt_num(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.2f}"


class GenerateInsights:
    def __init__(
        self,
        repository: DatasetRepository,
        max_insights: int = 8,
        max_metrics: int = 8,
        max_categories: int = 5,
    ) -> None:
        self._repository = repository
        self._max_insights = max_insights
        self._max_metrics = max_metrics
        self._max_categories = max_categories

    def execute(self, dataset_id: str) -> list[Insight]:
        dataset = self._repository.get(dataset_id)
        table = dataset.table
        columns = table.columns()

        date_column = next((c.name for c in columns if c.kind == ColumnKind.DATETIME), None)
        metrics = [c.name for c in columns if c.kind == ColumnKind.NUMERIC][: self._max_metrics]
        categories = [
            c.name
            for c in columns
            if c.kind == ColumnKind.CATEGORICAL and 1 < c.unique <= 25
        ][: self._max_categories]

        insights: list[Insight] = []
        if date_column:
            insights.extend(self._trend_insights(table, date_column, metrics))
            insights.extend(self._mover_insights(table, date_column, metrics, categories))
        insights.extend(self._correlation_insights(table))
        insights.extend(self._concentration_insights(table, metrics, categories))
        insights.extend(self._missing_insights(columns))

        insights.sort(key=lambda i: abs(i.magnitude), reverse=True)
        return insights[: self._max_insights]

    def _trend_insights(
        self, table: DataTable, date_column: str, metrics: list[str]
    ) -> list[Insight]:
        result = []
        for metric in metrics:
            changes = table.halves_change(date_column, metric, by=None)
            for change in changes:
                if change.change_pct is None or abs(change.change_pct) < 5:
                    continue
                direction = "вырос" if change.change_pct > 0 else "снизился"
                result.append(
                    Insight(
                        kind="trend",
                        title=f"{metric} {direction} на {_fmt_pct(change.change_pct).lstrip('+')}",
                        detail=(
                            f"Средний {metric} изменился с {_fmt_num(change.first)} "
                            f"в первой половине периода до {_fmt_num(change.second)} во второй "
                            f"({_fmt_pct(change.change_pct)})."
                        ),
                        magnitude=change.change_pct,
                    )
                )
        return result

    def _mover_insights(
        self,
        table: DataTable,
        date_column: str,
        metrics: list[str],
        categories: list[str],
    ) -> list[Insight]:
        result = []
        for category in categories:
            for metric in metrics:
                changes = [
                    c
                    for c in table.halves_change(date_column, metric, by=category)
                    if c.change_pct is not None and abs(c.change_pct) >= 15
                ]
                if not changes:
                    continue
                top = max(changes, key=lambda c: abs(c.change_pct or 0))
                direction = "вырос" if (top.change_pct or 0) > 0 else "упал"
                result.append(
                    Insight(
                        kind="mover",
                        title=f"{category} «{top.label}»: {metric} {direction} на {_fmt_pct(top.change_pct or 0).lstrip('+')}",
                        detail=(
                            f"Для {category} = «{top.label}» средний {metric} изменился "
                            f"с {_fmt_num(top.first)} до {_fmt_num(top.second)} "
                            f"между первой и второй половиной периода ({_fmt_pct(top.change_pct or 0)})."
                        ),
                        magnitude=top.change_pct or 0,
                    )
                )
        return result

    def _correlation_insights(self, table: DataTable) -> list[Insight]:
        result = []
        for pair in table.correlation_pairs(limit=2):
            if abs(pair.value) < 0.5:
                continue
            relation = "прямая" if pair.value > 0 else "обратная"
            result.append(
                Insight(
                    kind="correlation",
                    title=f"Связь между {pair.left} и {pair.right}",
                    detail=(
                        f"Между {pair.left} и {pair.right} наблюдается {relation} "
                        f"корреляция ({pair.value:.2f})."
                    ),
                    magnitude=pair.value * 100,
                )
            )
        return result

    def _concentration_insights(
        self, table: DataTable, metrics: list[str], categories: list[str]
    ) -> list[Insight]:
        result = []
        metric = metrics[0] if metrics else None
        aggregation = Aggregation.SUM if metric else Aggregation.COUNT
        for category in categories:
            groups = table.group_by(by=category, metric=metric, aggregation=aggregation, filters=[])
            total = sum(abs(float(g.value)) for g in groups)
            if not groups or total == 0:
                continue
            top = max(groups, key=lambda g: abs(float(g.value)))
            share = abs(float(top.value)) / total * 100
            if share < 40:
                continue
            result.append(
                Insight(
                    kind="concentration",
                    title=f"Концентрация в {category}: «{top.label}» — {share:.0f}%",
                    detail=(
                        f"На «{top.label}» приходится {share:.0f}% "
                        f"суммарного {metric or 'количества строк'} по {category}."
                    ),
                    magnitude=share,
                )
            )
        return result

    def _missing_insights(self, columns) -> list[Insight]:
        gaps = [(c.name, c.missing) for c in columns if c.missing > 0]
        if not gaps:
            return []
        worst = max(gaps, key=lambda g: g[1])
        total = sum(g[1] for g in gaps)
        return [
            Insight(
                kind="quality",
                title=f"Пропуски в данных: {total} значений",
                detail=(
                    f"Пропущенные значения найдены в {len(gaps)} колонках, "
                    f"больше всего в «{worst[0]}» ({worst[1]})."
                ),
                magnitude=float(total),
            )
        ]

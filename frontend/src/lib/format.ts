export function formatNumber(value: number | string | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (Number.isNaN(value)) return "—";
  if (Number.isInteger(value) && Math.abs(value) < 1_000_000) {
    return value.toLocaleString("ru-RU");
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("ru-RU", { maximumFractionDigits: 2 })} млн`;
  }
  return value.toLocaleString("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

export function formatCell(value: string | number | boolean | null): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    return value.toLocaleString("ru-RU", { maximumFractionDigits: 6 });
  }
  if (typeof value === "boolean") return value ? "да" : "нет";
  return String(value);
}

export const KIND_LABELS: Record<string, string> = {
  numeric: "число",
  categorical: "категория",
  datetime: "дата",
  text: "текст",
  boolean: "логич.",
};

export const AGG_LABELS: Record<string, string> = {
  sum: "сумма",
  mean: "среднее",
  median: "медиана",
  min: "минимум",
  max: "максимум",
  count: "количество",
};

export const FREQ_LABELS: Record<string, string> = {
  day: "день",
  week: "неделя",
  month: "месяц",
  quarter: "квартал",
};

export const OPERATOR_LABELS: Record<string, string> = {
  eq: "=",
  neq: "≠",
  gt: ">",
  gte: "≥",
  lt: "<",
  lte: "≤",
  contains: "содержит",
  in: "из списка",
};

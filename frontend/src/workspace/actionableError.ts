export function actionableErrorDetail(detail: unknown): string | null {
  if (typeof detail !== "object" || detail === null || !("detail" in detail)) return null;
  const value = detail.detail;
  if (typeof value === "string") return value;
  if (!Array.isArray(value)) return null;
  const messages = value.flatMap((item: unknown) => {
    if (typeof item !== "object" || item === null || !("msg" in item) || typeof item.msg !== "string") return [];
    const location = "loc" in item && Array.isArray(item.loc) ? item.loc.map(String).join(" → ") : "Input";
    return [`${location}: ${item.msg}`];
  });
  return messages.length === 0 ? null : messages.slice(0, 3).join(" ");
}

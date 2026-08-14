export type DocumentCategory = "pdf" | "mail" | "excel" | "word" | "powerpoint" | "bild" | "sonstige";

export function categorize(mimetype: string | null, dateiname: string): DocumentCategory {
  const ext = dateiname.split(".").pop()?.toLowerCase() ?? "";
  const mt = mimetype ?? "";
  if (mt.includes("pdf") || ext === "pdf") return "pdf";
  if (mt.includes("rfc822") || ext === "eml" || ext === "msg") return "mail";
  if (mt.includes("spreadsheet") || mt.includes("excel") || ["xlsx", "xls", "csv"].includes(ext)) return "excel";
  if (mt.includes("wordprocessing") || mt.includes("msword") || ["docx", "doc"].includes(ext)) return "word";
  if (mt.includes("presentation") || ["pptx", "ppt"].includes(ext)) return "powerpoint";
  if (mt.startsWith("image/") || ["png", "jpg", "jpeg", "gif", "svg", "webp"].includes(ext)) return "bild";
  return "sonstige";
}

export const CATEGORY_LABELS: Record<DocumentCategory, string> = {
  pdf: "PDF",
  mail: "Mail",
  excel: "Excel",
  word: "Word",
  powerpoint: "PowerPoint",
  bild: "Bild",
  sonstige: "Sonstige",
};

export const CATEGORY_ICONS: Record<DocumentCategory, string> = {
  pdf: "📄",
  mail: "📧",
  excel: "📊",
  word: "📝",
  powerpoint: "📽️",
  bild: "🖼️",
  sonstige: "📎",
};

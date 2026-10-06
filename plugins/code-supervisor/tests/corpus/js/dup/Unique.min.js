function slugify(title, separator) {
  const lowered = title.toLowerCase();
  const trimmed = lowered.trim();
  const parts = trimmed.split(" ");
  const joined = parts.join(separator);
  const cleaned = joined.replace(/[^a-z0-9-]/g, "");
  return cleaned;
}

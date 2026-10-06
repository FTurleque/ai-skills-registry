class RootsTarget {
    String render(String title, int level, String body) {
        String safeTitle = title.replace("<", "").replace(">", "");
        String heading = "#".repeat(Math.max(level, 1)) + " " + safeTitle;
        String trimmed = body.strip();
        String wrapped = trimmed.isEmpty() ? "(empty)" : trimmed;
        String section = heading + "\n\n" + wrapped;
        return section;
    }
}

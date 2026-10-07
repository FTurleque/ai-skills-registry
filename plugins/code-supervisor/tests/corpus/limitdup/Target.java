class LimitTarget {
    String describe(String name, int count, String unit) {
        String label = name.trim().toLowerCase();
        String plural = count == 1 ? unit : unit + "s";
        String prefix = count > 99 ? "many" : String.valueOf(count);
        String joined = prefix + " " + plural;
        String result = label + ": " + joined;
        return result;
    }
}

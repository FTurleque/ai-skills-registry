class CatchDocumentation {
  Object silent(String s) {
    try { return parse(s); } catch (IllegalArgumentException e) {
      return null;
    }
  }
  Object documented(String s) {
    try { return Integer.valueOf(s); } catch (IllegalArgumentException e) {
      // the caller reads a missing value as "not a number"
      return null;
    }
  }
  String diagnostic(String s) {
    try { return parse(s).toString(); } catch (IllegalArgumentException e) {
      return "could not parse the value";
    }
  }
  int counted(String[] rules, int[] discarded) {
    try { return rules.length; } catch (IllegalArgumentException e) {
      discarded[0]++;
      return 0;
    }
  }
  Object parse(String s) { return s; }
}

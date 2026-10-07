class FieldsA {
  private final String alpha;
  private final String beta;
  private final String gamma;
  private final String delta;
  private final String epsilon;
  private final String zeta;
  private final String eta;
  FieldsA(String seed) {
    alpha = seed.trim();
    beta = seed.toUpperCase();
    gamma = seed.toLowerCase();
    delta = seed.strip();
    epsilon = seed.intern();
    zeta = seed.concat("z");
    eta = seed.repeat(2);
  }
}

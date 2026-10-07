class C {
  void m1() {
    try { run(); } catch (Exception e) {
      // y
    }
  }
  void m23() {
    try { run(); } catch (Exception e) {
      // xxxxxxxxxxxxxxxxxxxxxxy
    }
  }
  void m24() {
    try { run(); } catch (Exception e) {
      // xxxxxxxxxxxxxxxxxxxxxxxy
    }
  }
  void m25() {
    try { run(); } catch (Exception e) {
      // xxxxxxxxxxxxxxxxxxxxxxxxy
    }
  }
  void m26() {
    try { run(); } catch (Exception e) {
      // xxxxxxxxxxxxxxxxxxxxxxxxxy
    }
  }
  void m60() {
    try { run(); } catch (Exception e) {
      // xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxy
    }
  }
}

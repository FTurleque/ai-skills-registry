class TempDirNaming {
  @TempDir java.nio.file.Path temp;
  void param(@TempDir java.nio.file.Path tmp) { }
  void plainVariable() {
    String temp = "x";
  }
}

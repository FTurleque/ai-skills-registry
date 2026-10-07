class BoundedWait {
  void polling(java.nio.file.Path path) throws InterruptedException {
    long deadline = System.nanoTime() + 1000L;
    while (!java.nio.file.Files.exists(path) && System.nanoTime() < deadline) Thread.sleep(50L);
  }
  void fixedPause() throws InterruptedException {
    Thread.sleep(5000L);
  }
  void unboundedLoop(java.nio.file.Path path) throws InterruptedException {
    while (!java.nio.file.Files.exists(path)) {
      Thread.sleep(50L);
    }
  }
}

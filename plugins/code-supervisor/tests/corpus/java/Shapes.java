package demo;

public interface Shapes {
    double area();
    double perimeter();
    default String label() { return "shape"; }
    static Shapes unit() { return null; }
}

record Point(int x, int y) {
    int sum() { return x + y; }
}

abstract class Base {
    abstract void run();
    public synchronized void guarded() throws java.io.IOException, java.sql.SQLException, java.lang.IllegalStateException, java.util.concurrent.TimeoutException {
        run();
    }
    protected static final int constant() { return 1; }
}

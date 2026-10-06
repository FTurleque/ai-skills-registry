class DuplicateSelf {
    int first(int a, int b) {
        int sum = a + b;
        int product = a * b;
        int result = sum * product;
        if (result > 100) { return 100; }
        return result;
    }

    int second(int c, int d) {
        int sum = c + d;
        int product = c * d;
        int result = sum * product;
        if (result > 100) { return 100; }
        return result;
    }
}

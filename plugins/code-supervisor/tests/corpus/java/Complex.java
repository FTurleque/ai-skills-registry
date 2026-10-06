package demo;

import java.util.List;
import java.util.Optional;

public class Complex {
    public int tooMany(int a, int b, int c, int d, int e, int f, int g) {
        return a + b + c + d + e + f + g;
    }

    public int nested(int a, int b) {
        if (a > 0) {
            for (int i = 0; i < b; i++) {
                while (i < a) {
                    if (i == b) {
                        switch (a) {
                            case 1:
                                return 1;
                            default:
                                break;
                        }
                    }
                    i++;
                }
            }
        }
        return 0;
    }

    public int branchy(int v) {
        if (v == 1) { return 1; }
        if (v == 2) { return 2; }
        if (v == 3) { return 3; }
        if (v == 4) { return 4; }
        if (v == 5) { return 5; }
        if (v == 6) { return 6; }
        if (v == 7) { return 7; }
        if (v == 8) { return 8; }
        if (v == 9) { return 9; }
        if (v == 10) { return 10; }
        if (v == 11) { return 11; }
        if (v == 12) { return 12; }
        if (v == 13) { return 13; }
        if (v == 14) { return 14; }
        if (v == 15) { return 15; }
        if (v == 16) { return 16; }
        if (v == 17) { return 17; }
        return 0;
    }

    public boolean condition(boolean a, boolean b, boolean c, boolean d, boolean e) {
        return (a && b) || (c && d) || (e && a) || (b && c);
    }

    public int average(List<Integer> values) {
        int sum = 0;
        int count = values.size();
        for (int each : values) {
            sum += each;
        }
        return sum / count;
    }

    public int guardedByCompare(List<Integer> values) {
        int count = values.size();
        if (count > 0) {
            return 100 / count;
        }
        return 0;
    }

    public int guardedByDifference(List<Integer> values) {
        int count = values.size();
        if (count != 0) {
            return 100 / count;
        }
        return 0;
    }

    public int guardedByEmptiness(List<Integer> values) {
        int total = values.size();
        if (values.isEmpty()) {
            return 0;
        }
        return 100 / total;
    }

    public int unguardedTotal(List<Integer> values) {
        int total = values.size();
        return 100 / total;
    }

    public int divisionBySize() {
        return 100 / size();
    }

    public String optional(String raw) {
        Optional<String> maybe = Optional.ofNullable(raw);
        return maybe.get();
    }

    public void concurrent(List<String> items) {
        for (String item : items) {
            items.remove(item);
        }
    }

    public int longMethod(int v) {
        int total = 0;
        total += v;
        total += v + 1;
        total += v + 2;
        total += v + 3;
        total += v + 4;
        total += v + 5;
        total += v + 6;
        total += v + 7;
        total += v + 8;
        total += v + 9;
        total += v + 10;
        total += v + 11;
        total += v + 12;
        total += v + 13;
        total += v + 14;
        return total;
    }
}

package demo;

public class DuplicateB {
    public double quoteTotal(double base, double rate) {
        double discounted = base * 0.9;
        double taxed = discounted * (1 + rate);
        double rounded = Math.round(taxed * 100.0) / 100.0;
        if (rounded < 0) {
            return 0;
        }
        return rounded;
    }
}

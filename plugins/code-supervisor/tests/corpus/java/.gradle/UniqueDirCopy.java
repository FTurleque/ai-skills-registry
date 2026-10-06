class UniqueDirCopy {
    double shipping(double weight, double distance) {
        double base = weight * 1.5;
        double surcharge = distance * 0.25;
        double total = base + surcharge;
        if (total > 500) { total = 500; }
        double rounded = Math.round(total * 100.0) / 100.0;
        return rounded;
    }
}

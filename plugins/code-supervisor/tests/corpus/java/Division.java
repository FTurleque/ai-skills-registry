public class Division {
    public int byReceiverSize(java.util.List<Integer> values) {
        return 100 / values.size();
    }

    public int byLength(int[] items) {
        return 100 / items.length;
    }

    public int byMethodLength(String text) {
        return 100 / text.length();
    }

    public int byChainedCount(Stats stats) {
        return 100 / stats.summary.count;
    }

    public int guardedReceiver(java.util.List<Integer> values) {
        if (values.isEmpty()) {
            return 0;
        }
        return 100 / values.size();
    }

    public int notADivisor(int[] items) {
        return items.length / 2;
    }

    public int otherNames(Config config) {
        return 100 / config.sizeLimit + 100 / config.counter;
    }

    public int commentedOut(int[] items) {
        // return 100 / items.length;
        return 0;
    }
}

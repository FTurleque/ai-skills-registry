class CrossRoot {
    int clamp(int value, int low, int high) {
        int bounded = value;
        if (bounded < low) { bounded = low; }
        if (bounded > high) { bounded = high; }
        int range = high - low;
        int offset = bounded - low;
        return offset * 100 / range;
    }
}

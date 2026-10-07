class UniquePlainCopy {
    long checksum(long seed, long salt) {
        long folded = seed ^ salt;
        long shifted = folded << 3;
        long mixed = shifted + folded;
        while (mixed > 1000000) { mixed = mixed / 7; }
        long masked = mixed & 255;
        return masked;
    }
}

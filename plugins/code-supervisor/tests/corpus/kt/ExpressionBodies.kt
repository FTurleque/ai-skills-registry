class Counter(var total: Int) {
    fun double(x: Int) = x * 2
    fun describe(x: Int): String = "value " + x
    fun pick(x: Int) = if (x > 0) { 1 } else { 2 }
    fun reset(): Int {
        total = 0
        return total
    }
}

fun last(x: Int) = x + 1

fun withSemicolonLater(x: Int) = x * 2
val first = 1; val second = 2

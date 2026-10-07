class Greeter(val name: String) {
    fun greet(other: String): String {
        return "hi " + other
    }
    private fun twice(x: Int) = x * 2
    suspend fun load(id: Int): Int { return id }
}

fun topLevel(a: Int, b: Int): Int { return a + b }

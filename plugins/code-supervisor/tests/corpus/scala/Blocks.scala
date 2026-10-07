object Blocks {
  def compute(x: Int): Int = {
    val doubled = x * 2
    doubled + 1
  }

  def inline(x: Int) = x + 1

  def pad(x: Int): String = {
    "v" + x
  }
}

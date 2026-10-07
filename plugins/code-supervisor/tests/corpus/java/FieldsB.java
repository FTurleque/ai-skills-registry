class FieldsB {
  private final String first;
  private final String second;
  private final String third;
  private final String fourth;
  private final String fifth;
  private final String sixth;
  private final String seventh;
  FieldsB(int count) {
    first = Integer.toString(count);
    second = Integer.toHexString(count);
    third = Integer.toBinaryString(count);
    fourth = Integer.toOctalString(count);
    fifth = String.valueOf(count * 2);
    sixth = String.valueOf(count + 1);
    seventh = String.valueOf(count - 1);
  }
}

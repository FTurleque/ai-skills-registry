function outer(a) {
  function inner(b) {
    return b + 1;
  }
  const arrow = (c) => c + 1;
  return inner(a);
}

class Widget {
  render() { return 1; }
  static make(opts) { return new Widget(); }
}

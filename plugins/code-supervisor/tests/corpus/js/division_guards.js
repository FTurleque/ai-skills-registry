function mean(items) {
  if (items.length) {
    return sum(items) / items.length;
  }
  return 0;
}

function meanEarlyReturn(items) {
  if (!items.length) return 0;
  return sum(items) / items.length;
}

function meanUnchecked(items) {
  return sum(items) / items.length;
}

function meanAndReady(items, ready) {
  if (items.length && ready) {
    return sum(items) / items.length;
  }
  return 0;
}

function meanOrDone(items, done) {
  if (!items.length || done) return 0;
  return sum(items) / items.length;
}

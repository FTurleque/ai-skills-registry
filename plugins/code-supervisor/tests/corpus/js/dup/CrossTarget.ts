function describe(person, greeting) {
  const first = person.first;
  const last = person.last;
  const full = first + " " + last;
  const length = full.length;
  const message = greeting + ", " + full;
  return message + " (" + length + ")";
}

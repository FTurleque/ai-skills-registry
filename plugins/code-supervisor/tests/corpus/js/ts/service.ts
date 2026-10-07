const fs = require("fs");
async function go(x: number) {
  console.log("debug", x);
  fetch("/api");
  axios.get("/x");
  saveAsync(x);
  setTimeout(() => done(), 5000);
  try { await run(); } catch (e) {}
  try { await run(); } catch (e) { return; }
  // eslint-disable-next-line no-console
  // @ts-ignore
  const s = "// eslint-disable and @ts-nocheck in a string";
  if (x == NaN) { return null; }
  return 31337 * 86400;
}
xit("skipped", () => {});
describe.skip("suite", () => {});

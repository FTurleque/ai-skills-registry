const crypto = require("crypto");
const cp = require("child_process");
const https = require("https");

function render(req, res, userInput) {
  document.getElementById("out").innerHTML = userInput;
  document.write(userInput);
  eval(userInput);
  cp.exec("ls " + req.query.dir);
  crypto.createHash("md5").update(userInput);
  https.get({ host: "internal", rejectUnauthorized: false });
  console.log("token", req.headers.authorization);
  return fs.readFileSync(req.query.file);
}

const fs = require("fs");
const path = require("path");
const async = require("async");
const ProgressBar = require("progress");

const config = require("./config");

const fileContent = fs
  .readFileSync(__dirname + "/../java_repos.txt")
  .toString();
const repos = fileContent.split("\n");

let truncated = 0;

var bar = new ProgressBar("[:bar] :current :rate/bps :percent :etas :repo", {
  complete: "=",
  incomplete: " ",
  width: 80,
  total: repos.length,
});

const ingoredFolders = ["siteMods", "userguide", "resources", "sample", "example", "test/"]
async.eachLimit(repos, 15, (repo, callback) => {
  bar.tick({
    repo: repo,
  });
  const pathFile = path.join(config.output, repo, "project-files.json");
  if (!fs.existsSync(pathFile)) {
    return callback();
  }

  const repositoryContent = JSON.parse(fs.readFileSync(pathFile));

  if (repositoryContent.truncated) {
    truncated++;
  }

  const poms = [];
  for (let i of repositoryContent.tree) {
    if (i.size < 5) {
      continue;
    }
    const filename = i.path.substring(
      i.path.lastIndexOf("/") + 1,
      i.path.length
    );

    if (filename.toLowerCase() == "pom.xml") {
      let toIgnore = false;
      // ignore pom.xml from a defined list of folder
      for (let ign of ingoredFolders) {
        if (i.path.indexOf(ign) != -1) {
          toIgnore = true
          break;
        }
      }

      if (toIgnore == false) {
        poms.push(i.path);
        console.log(i.path)
      }
    }
  }
  if (poms.length != 1) {
    return callback();
  }

  const pathOutput = path.join(config.output, repo, "project-poms.json")
  if (!fs.existsSync(path.dirname(pathOutput))) {
    fs.mkdirSync(path.dirname(pathOutput), { recursive: true });
  }
  fs.writeFileSync(pathOutput, JSON.stringify(poms, null, 1));

  callback();
});

console.log("# Truncated file lists", truncated);

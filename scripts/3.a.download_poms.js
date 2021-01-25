const fs = require("fs");
const path = require("path");
const async = require("async");
const ProgressBar = require("progress");

const config = require("./config");
const utils = require("./utils");

const OUTPUT_dir = config.output + "poms/";
if (!fs.existsSync(OUTPUT_dir)) {
  fs.mkdirSync(OUTPUT_dir);
}

const fileContent = fs
  .readFileSync(__dirname + "/../java_repos.txt")
  .toString();
const repos = fileContent.split("\n");

var bar = new ProgressBar("[:bar] :current :rate/bps :percent :etas :repo", {
  complete: "=",
  incomplete: " ",
  width: 80,
  total: repos.length,
});

function downloadGitHubFile(repo, file, commit, callback) {
  utils.downloadGithubFile(repo, commit, file, config.github_tokens[0]).then(
    (res) => callback(null, res),
    (res) => callback(res, null)
  );
}

let nbMaven = 0;
async.eachLimit(
  repos.reverse(),
  10,
  (repo, callback) => {
    bar.tick({
      repo: repo,
    });
    const pathPomList = path.join(config.output, repo, "project-poms.json")
    if (!fs.existsSync(pathPomList)) {
      return callback();
    }
    const pathFileList = path.join(config.output, repo, "project-files.json")
    if (!fs.existsSync(pathFileList)) {
      return callback();
    }
    const fileList = JSON.parse(fs.readFileSync(pathFileList));
    const commit = fileList.sha;
    const pathPom = path.join(config.output, repo, "commits", commit, "pom.xml")
    if (fs.existsSync(pathPom)) {
      nbMaven++;
      return callback();
    }

    if (!fs.existsSync(path.dirname(pathPom))) {
      fs.mkdirSync(path.dirname(pathPom), {recursive: true})
    }
    
    fs.readFile(pathPomList, (err, data) => {
      if (err) {
        console.error(err);
        return callback();
      }
      const poms = JSON.parse(data);
      if (poms.length > 0) {
        nbMaven++;
      }
      if (poms.length == 1) {
        if (!fs.existsSync(path.dirname(pathPom))) {
          fs.mkdirSync(path.dirname(pathPom), { recursive: true });
        }
        downloadGitHubFile(repo, poms[0], commit, (err, body) => {
          if (err == null) {
            fs.writeFileSync(pathPom, body);
          }
          callback();
        });
      } else {
        callback();
      }
    });
  },
  () => {
    console.log("# pom downloaded", nbMaven);
  }
);

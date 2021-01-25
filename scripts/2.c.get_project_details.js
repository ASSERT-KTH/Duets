const async = require("async");
const fs = require("fs");
const path = require("path");
const ProgressBar = require("progress");

const config = require("./config");
const utils = require("./utils");

const tokens = {};
for (let token of config.github_tokens) {
  tokens[token] = {};
}

const fileContent = fs
  .readFileSync(__dirname + "/../java_repos.txt")
  .toString();
const repos = fileContent.split("\n");

var bar = new ProgressBar("[:bar] :current :rate/bps :percent :etas :step", {
  complete: "=",
  incomplete: " ",
  width: 30,
  total: repos.length,
});

const available_tokens = [...config.github_tokens];
async.eachOfLimit(
  utils.shuffle(repos),
  available_tokens.length,
  (item, index, callback) => {
    bar.tick({
      step: item,
    });

    const files_path = path.join(config.output, repo, "project-info.json")
    if (fs.existsSync(files_path)) {
      return callback();
    }
    const token = available_tokens.pop();

    const octokit = utils.createOctokit(token);

    const owner = item.split("/")[0];
    const repo = item.split("/")[1];

    octokit.repos
      .get({ owner, repo })
      .then(
        (response) => {
          if (!fs.existsSync(path.dirname(files_path))) {
            fs.mkdirSync(path.dirname(files_path), {recursive: true});
          }
          const details = utils.clean_github_object(response.data);
          fs.writeFile(files_path, JSON.stringify(details), (err) => {
            available_tokens.push(token);
            if (err) {
              console.error(err);
            }
            callback();
          });
        },
        (err) => {
          console.error(err.message, owner, repo);
          available_tokens.push(token);
          callback();
        }
      );
  }
);

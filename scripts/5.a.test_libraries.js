const fs = require("fs");
const ProgressBar = require("progress");
const async = require("async");
var exec = require("child_process").exec;

const config = require("./config");
const utils = require("./utils");

let mavenGraph = JSON.parse(
  fs.readFileSync(__dirname + "/maven_graph_with_release.json")
);
let results = {};
if (fs.existsSync(__dirname + "/maven_graph_with_test_results.json")) {
  results = JSON.parse(
    fs.readFileSync(__dirname + "/maven_graph_with_test_results.json")
  );
}

function execTest(repo, commit) {
  return new Promise((resolve) => {
    exec(
      `docker run --rm jdbl compile --url https://github.com/${repo} --commit ${commit}`,
      (error, stdout, stderr) => {
        if (!error && stdout) {
          try {
            return resolve(JSON.parse(stdout));
          } catch (error) { }
        }
        resolve(null);
      }
    );
  });
}

(async () => {
  const tasks = [];
  for (let libId in mavenGraph) {
    const lib = mavenGraph[libId];
    const resultsLib = results[libId];
    for (let version in lib.clients) {
      const commit = lib.releases[version];
      if (resultsLib && resultsLib.test_results) {
        if (!lib.test_results) {
          lib.test_results = resultsLib.test_results;
        }
      }

      if (
        lib.test_results &&
        lib.test_results[commit] &&
        lib.test_results[commit].length >= 3
      ) {
        continue;
      }
      tasks.push({
        lib,
        repo: lib.repo_name,
        commit,
      });
    }
  }
  var bar = new ProgressBar(
    "[:bar] :current/:total (:percent) :rate/bps :etas :step",
    {
      complete: "=",
      incomplete: " ",
      width: 30,
      total: tasks.length,
    }
  );
  async.eachOfLimit(utils.shuffle(tasks), 15, async (task, index) => {
    if (!task.lib.test_results) {
      task.lib.test_results = {};
    }
    if (!task.lib.test_results[task.commit]) {
      task.lib.test_results[task.commit] = [];
    }
    const results = await execTest(task.repo, task.commit);
    if (results != null) {
      task.lib.test_results[task.commit] = results.test_results;
    }
    fs.writeFileSync(
      __dirname + "/maven_graph_with_test_results.json",
      JSON.stringify(mavenGraph)
    );

    bar.tick({
      step: `${task.repo} ${task.commit}`,
    });
  });
})();

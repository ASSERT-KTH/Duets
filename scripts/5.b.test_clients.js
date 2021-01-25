const fs = require("fs");
const ProgressBar = require("progress");
const async = require("async");
var exec = require("child_process").exec;

const config = require("./config");
const utils = require("./utils");

let mavenGraph = JSON.parse(
  fs.readFileSync(__dirname + "/maven_graph_with_test_results.json")
);
let results = {};
if (
  fs.existsSync(__dirname + "/maven_graph_with_client_test_results.json")
) {
  results = JSON.parse(
    fs.readFileSync(__dirname + "/maven_graph_with_client_test_results.json")
  );
}

function execTest(repo, commit) {
  return new Promise((resolve) => {
    exec(
      `timeout -k 1m -s 9 1h docker run --rm jdbl compile --url https://github.com/${repo} --commit ${commit}`,
      (error, stdout, stderr) => {
        if (!error && stdout) {
          try {
            const results = JSON.parse(stdout);
            return resolve(results);
          } catch (error) {}
        }
        resolve(null);
      }
    );
  });
}

(async () => {
  const tasks = [];
  const testExecutionResults = {};
  for (let libId in mavenGraph) {
    const lib = mavenGraph[libId];
    const resultsLib = results[libId];
    version: for (let version in lib.clients) {
      const commit = lib.releases[version];
      if (
        !lib.test_results ||
        !lib.test_results[commit] ||
        lib.test_results[commit].length != 3
      ) {
        continue;
      }
      for (let r of lib.test_results[commit]) {
        if (r == null) {
          continue version;
        }
        if (r.error != 0 || r.failing != 0 || r.passing == 0) {
          continue version;
        }
      }
      const clients = lib.clients[version];
      for (let client of clients) {
        if (resultsLib && resultsLib.clients[version] && !client.test_results) {
          for (let c of resultsLib.clients[version]) {
            if (c.repo_name == client.repo_name) {
              if (c.test_results) {
                client.test_results = c.test_results;
              }
              break;
            }
          }
        }
        if (client.test_results || !client.commit) {
          continue;
        }
        tasks.push({
          lib,
          client,
          repo: client.repo_name,
        });
      }
    }
  }
  fs.writeFileSync(
    __dirname + "/maven_graph_with_client_test_results.json",
    JSON.stringify(mavenGraph)
  );
  var bar = new ProgressBar(
    "[:bar] :current/:total (:percent) :rate/bps :etas :step",
    {
      complete: "=",
      incomplete: " ",
      width: 30,
      total: tasks.length,
    }
  );
  async.eachOfLimit(utils.shuffle(tasks), 5, async (task, index) => {
    let results = null;
    if (testExecutionResults[task.repo] != null) {
      results = testExecutionResults[task.repo].test_results;
      task.client.commit = testExecutionResults[task.repo].commit;
    } else {
      results = await execTest(task.repo, "HEAD");
    }

    bar.tick({
      step: `${task.repo} for ${task.lib.repo_name}`,
    });
    if (results != null) {
      testExecutionResults[task.repo] = results;
      task.client.commit = results.commit;
      task.client.test_results = results.test_results;
    }

    fs.writeFileSync(
      __dirname + "/maven_graph_with_client_test_results.json",
      JSON.stringify(mavenGraph)
    );
  });
})();

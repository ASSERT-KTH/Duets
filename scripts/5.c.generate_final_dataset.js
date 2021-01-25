const fs = require("fs");

const config = require("./config");

let mavenGraph = JSON.parse(
  fs.readFileSync(__dirname + "/maven_graph_with_client_test_results.json")
);

(async () => {
  let count = 0;
  const testExecutionResults = {};
  const repoCommit = {};
  for (let libId in mavenGraph) {
    const lib = mavenGraph[libId];
    version: for (let version in lib.clients) {
      const commit = lib.releases[version];
      if (
        !lib.test_results ||
        !lib.test_results[commit] ||
        lib.test_results[commit].length != 3
      ) {
        delete lib.clients[version];
        continue;
      }

      const clients = [...lib.clients[version]];
      client: for (let i = clients.length - 1; i >= 0; i--) {
        const client = clients[i];
        if (!client.test_results || client.test_results.length != 3) {
          continue;
        }
        testExecutionResults[client.repo_name] = client.test_results;
        if (client.commit) {
          repoCommit[client.repo_name] = client.commit;
        }
      }
    }
  }

  for (let libId in mavenGraph) {
    count += 1;
    const lib = mavenGraph[libId];
    version: for (let version in lib.clients) {
      const commit = lib.releases[version];
      if (
        !lib.test_results ||
        !lib.test_results[commit] ||
        lib.test_results[commit].length != 3
      ) {
        delete lib.clients[version];
        continue;
      }
      for (let r of lib.test_results[commit]) {
        if (r == null) {
          delete lib.clients[version];
          continue version;
        }
        if (r.error != 0 || r.failing != 0 || r.passing == 0) {
          delete lib.clients[version];
          continue version;
        }
      }
      const clients = [...lib.clients[version]];
      client: for (let i = clients.length - 1; i >= 0; i--) {
        const client = clients[i];
        if (testExecutionResults[client.repo_name]) {
          client.test_results = testExecutionResults[client.repo_name];
        }
        if (!client.commit && repoCommit[client.repo_name]) {
          client.commit = repoCommit[client.repo_name]
        }
        if (!client.test_results || client.test_results.length != 3 || !client.commit) {
          lib.clients[version].splice(i, 1);
          continue;
        }
        for (let r of client.test_results) {
          if (r == null) {
            lib.clients[version].splice(i, 1);
            continue client;
          }
          if (r.error != 0 || r.failing != 0 || r.passing == 0) {
            if (true || r.passing == 0) {
              lib.clients[version].splice(i, 1);
            }
            continue client;
          }
        }
      }
      if (lib.clients[version].length == 0) {
        delete lib.clients[version];
      }
    }
    if (Object.keys(lib.clients).length == 0) {
      delete mavenGraph[libId];
    }
  }
  let countVersion = 0;
  let countClient = 0;
  for (let libId in mavenGraph) {
    const lib = mavenGraph[libId];
    let localCountVersion = 0;
    let localCountClient = 0;
    for (let version in lib.clients) {
      localCountVersion += 1;
      const clients = [...lib.clients[version]];
      for (let client in clients) {
        localCountClient += 1;
      }
    }
    countVersion += localCountVersion;
    countClient += localCountClient;
    // console.log(libId, localCountVersion, localCountClient);
  }
  console.log(count, Object.keys(mavenGraph).length, countVersion, countClient);
  fs.writeFileSync(
    config.output + "dataset-info.json",
    JSON.stringify(mavenGraph)
  );
})();

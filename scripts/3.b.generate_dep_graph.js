const pomParser = require("pom-parser");
const fs = require("fs");
const path = require("path");
const async = require("async");
const ProgressBar = require("progress");

const config = require("./config");
const utils = require("./utils");

const fileContent = fs
  .readFileSync(__dirname + "/../java_repos.txt")
  .toString();
const repos = fileContent.split("\n");

var bar = new ProgressBar("[:bar] :current/:total (:percent) :rate/bps :etas :repo", {
  complete: "=",
  incomplete: " ",
  width: 80,
  total: repos.length,
});
const deps = {};

const toConsider = new Set();
const mapIdToInfo = {};

async.eachLimit(
  repos,
  15,
  (repo, callback) => {
    bar.tick({
      repo: repo,
    });
    const pomPaths = utils.walkSync(path.join(config.output, repo, 'commits')).filter(f => f.indexOf("pom.xml") > -1);
    async.eachLimit(pomPaths, 1, (filePath, callback) => {
      pomParser.parse(
        { filePath },
        function (err, pomResponse) {
          if (err || pomResponse.pomObject.project == null) {
            // fs.unlinkSync(file)
            // console.log(repo, err)
            return callback();
          }
          const pom = pomResponse.pomObject.project;
          let groupId = pom.groupid;
          if (groupId == null && pom.parent != null) {
            groupId = pom.parent.groupid;
          }
          let artifactId = pom.artifactid;
          if (artifactId == null && pom.parent != null) {
            artifactId = pom.parent.artifactId;
          }
          const projectDeps = new Set();
          const javaVersion = utils.getJavaVersion(pom);
          let parentId = utils.removeEndNumber(groupId + ":" + artifactId);
          if (mapIdToInfo[parentId]) {
            const previousRepoDetail = path.join(config.output, mapIdToInfo[parentId].repo_name, "project-info.json")
            const newRepoDetail = path.join(config.output, repo, "project-info.json")
            const previousRepo = JSON.parse(fs.readFileSync(previousRepoDetail));
            const newRepo = JSON.parse(fs.readFileSync(newRepoDetail));

            if (previousRepo.stargazers_count < newRepo.stargazers_count) {
              console.log("Change", mapIdToInfo[parentId].repo_name, "to", repo);
              mapIdToInfo[parentId].repo_name = repo;
              mapIdToInfo[parentId].javaVersion = javaVersion;
              mapIdToInfo[parentId].version = utils.getVersion(pom, pom.version);
            }
          } else {
            mapIdToInfo[parentId] = {
              repo_name: repo,
              groupId: groupId,
              artifactId: artifactId,
              version: utils.getVersion(pom, pom.version),
              java_version: javaVersion,
            };
          }
          if (pom.dependencies && pom.dependencies.dependency) {
            if (!Array.isArray(pom.dependencies.dependency)) {
              pom.dependencies.dependency = [pom.dependencies.dependency];
            }
            for (let dependency of pom.dependencies.dependency) {
              let id = utils.removeEndNumber(
                dependency.groupid + ":" + dependency.artifactid
              );
              projectDeps.add(id);
            }
            if (
              projectDeps.has("junit:junit") ||
              projectDeps.has("org.junit.jupiter:junit-jupiter")
            ) {
              const projectId = utils.removeEndNumber(groupId + ":" + artifactId);
              toConsider.add(projectId);
              for (let dependency of pom.dependencies.dependency) {
                let id = utils.removeEndNumber(
                  dependency.groupid + ":" + dependency.artifactid
                );
                if (!deps[id]) {
                  deps[id] = [];
                }
                let version = utils.getVersion(
                  pom,
                  dependency.version,
                  dependency.groupid,
                  dependency.artifactid
                );
                if (
                  version == null ||
                  version.length == 0 ||
                  version.indexOf("[") != -1 ||
                  version.toLocaleLowerCase().indexOf("snapshot") != -1 ||
                  version[0] == "$" ||
                  version == "RELEASE" ||
                  version == "LATEST"
                ) {
                  // ignore depency without an explicit release number
                  continue;
                }
                deps[id].push({
                  repo_name: repo,
                  groupId: groupId,
                  artifactId: artifactId,
                  version: version,
                });
              }
            }
          }
          callback();
        }
      );
    }, callback)
  },
  async () => {
    const output = {};
    console.log(toConsider.size);
    for (let dep of toConsider) {
      if (deps[dep] && deps[dep].length >= 10) {
        output[dep] = {
          artifactId: mapIdToInfo[dep].artifactId,
          groupId: mapIdToInfo[dep].groupId,
          repo_name: mapIdToInfo[dep].repo_name,
          java_version: mapIdToInfo[dep].java_version,
          version: mapIdToInfo[dep].version,
          clients: {},
        };
        for (let client of deps[dep]) {
          if (!output[dep].clients[client.version]) {
            output[dep].clients[client.version] = [];
          }
          output[dep].clients[client.version].push(client);
        }
      }
    }
    function getLen(element) {
      let count = 0;
      for (let i in element) {
        count += element[i].length;
      }
      return count;
    }
    const sortedLib = Object.keys(output).sort((a, b) => {
      return getLen(output[b].clients) - getLen(output[a].clients);
    });
    for (let i of sortedLib) {
      console.log(i, getLen(output[i].clients));
    }
    fs.writeFileSync(
      __dirname + "/maven_graph.json",
      JSON.stringify(output, null, 1)
    );
    console.log("File generated at: " + __dirname + "/maven_graph.json")
  }
);

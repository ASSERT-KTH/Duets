const fs = require("fs");
const path = require("path");
const ProgressBar = require("progress");

const config = require("./config");
const utils = require("./utils");

const available_tokens = [...config.github_tokens];


const mavenGraph = JSON.parse(fs.readFileSync(__dirname + "/maven_graph.json"));

async function downloadTags(lib) {
  const token = available_tokens.pop();
  const octokit = utils.createOctokit(token);

  const owner = lib.repo_name.split("/")[0];
  const repo = lib.repo_name.split("/")[1];

  const response = await octokit.repos.listTags({
    owner,
    repo,
  });

  if (!fs.existsSync(OUTPUT_dir + owner)) {
    fs.mkdirSync(OUTPUT_dir + owner);
  }
  const releases = utils.clean_github_object(response.data);

  fs.writeFileSync(
    path.join(config.output, lib.repo_name, "project-tags.json"),
    JSON.stringify(releases, null, 1)
  );
  available_tokens.push(token);
}

async function downloadPomCommits(lib) {
  const paths = JSON.parse(
    fs.readFileSync(path.join(config.output, lib.repo_name, "project-poms.json"))
  );
  const path = paths[0];

  const token = available_tokens.pop();
  const octokit = utils.createOctokit(token);

  const owner = lib.repo_name.split("/")[0];
  const repo = lib.repo_name.split("/")[1];

  const response = await octokit.paginate(octokit.repos.listCommits.endpoint.merge({
    owner,
    repo,
    path,
    per_page: 100
  }));
  if (!fs.existsSync(OUTPUT_POM_COMMIT_dir + owner)) {
    fs.mkdirSync(OUTPUT_POM_COMMIT_dir + owner);
  }
  const commits = utils
    .clean_github_object(response)
    .map((c) => c.sha)
    .reverse();

  const pathCommitList = path.join(config.output, lib.repo_name, "project-release-commits.json")
  fs.writeFileSync(pathCommitList, JSON.stringify(commits));
  available_tokens.push(token);
}

async function downloadPom(lib, commit) {
  const pathCommit = path.join(config.output, lib.repo_name, "commits", commit)
  const paths = JSON.parse(
    fs.readFileSync(path.join(config.output, lib.repo_name, "project-poms.json"))
  );
  const path = paths[0];
  const token = available_tokens.pop();

  const pom = await utils.downloadGithubFile(
    lib.repo_name,
    commit,
    path,
    token
  );

  if (!fs.existsSync(pathCommit)) {
    fs.mkdirSync(pathCommit, {recursive: true});
  }

  fs.writeFileSync(path.join(pathCommit, "pom.xml"), pom);
  available_tokens.push(token);
}

function normalizeVersion(version) {
  return version
    .toLowerCase()
    .replace("portable-", "")
    .replace("v.", "")
    .replace("v", "")
    .replace(/_/g, ".")
    .replace(/-/g, ".");
}

function findCommitForVersion(version, versionCommit) {
  if (versionCommit[version]) {
    return versionCommit[version];
  }
  version = normalizeVersion(version);
  for (let release in versionCommit) {
    const commit = versionCommit[release];
    release = normalizeVersion(release);
    let index = release.indexOf(version);
    if (index > -1) {
      return commit;
    }
  }
}
(async () => {
  var bar = new ProgressBar("[:bar] :current :rate/bps :percent :etas :step", {
    complete: "=",
    incomplete: " ",
    width: 30,
    total: Object.keys(mavenGraph).length,
  });

  let losts = 0;
  let valid = 0;
  for (let libId in mavenGraph) {
    const lib = mavenGraph[libId];

    bar.tick({
      step: libId,
    });

    const pathTags = path.join(config.output, lib.repo_name, "project-tags.json")
    if (!fs.existsSync(pathTags)) {
      await downloadTags(lib);
    }
    const versionCommit = {};
    for (let tag of JSON.parse(fs.readFileSync(pathTags))) {
      versionCommit[tag.name] = tag.commit.sha;
    }

    const pathCommitList = path.join(config.output, lib.repo_name, "project-release-commits.json")

    if (!fs.existsSync(pathCommitList)) {
      await downloadPomCommits(lib);
    }
    const commits = JSON.parse(fs.readFileSync(pathCommitList));

    for (let commit of commits) {
      const pathPom = path.join(config.output, lib.repo_name, "commits", commit, "pom.xml")
      if (!fs.existsSync(pathPom)) {
        try {
          await downloadPom(lib, commit);
        } catch (error) { }
      }
      try {
        const pom = await utils.parsePom(pathPom);
        if (!versionCommit[pom.version]) {
          versionCommit[pom.version] = commit;
        }
      } catch (error) { }
    }
    lib.releases = {};
    for (const clientVersion in lib.clients) {
      const commit = findCommitForVersion(clientVersion, versionCommit);
      if (commit == null) {
        delete lib.clients[clientVersion];
        losts += 1; // Object.keys(lib.clients[clientVersion]).length
      } else {
        valid += 1;
        lib.releases[clientVersion] = commit;
      }
    }

    if (Object.keys(lib.clients).length == 0) {
      delete mavenGraph[libId];
    }
  }
  fs.writeFileSync(__dirname + "/maven_graph_with_release.json", JSON.stringify(mavenGraph))
})();

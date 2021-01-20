# JDBL Dataset

# Metric

# Usage

The first step is to create the configuration file in `script/config.js`.
The file needs to contain the following information:
´´´js
module.exports = {
    "github_tokens": [], // the list of github tokens to collect data, the more the best
    output: __dirname + '/../data/' // where the data is stored
}
´´´

´´´bash
npm i;
node script/1.collect_project_files.js
node script/2.identify_single_module_maven_project.js
node script/3.get_poms.js
node script/4.get_project_details.js
node script/5.generate_dep_graph.js
node script/6.get_commit_for_version.js
node script/7.test_libraries.js
node script/8.test_clients.js
´´´
# Creation Steps

## 0. List of Java projects

147 991 Java projects from Github that has more than 5 stars, the list of projects is available at `data/java_project.txt`.

## 1. List all the file from all the projects

This step takes the 147 991 Java projects from Github, uses the GitHub API to list all the files from the projects.
The list of files is stored in `data/repo_files`.
We succeed to collect the list of files for 147 840 projects.

## 2. Identify the single module maven projects

The second step identifies the single module maven projects. We look in the list of files collected in step 1 if the project contains only one `pom.xml`.
The output of this step in a JSON file for each single module project that contains the path of the `pom.xml`.
The paths of the `pom.xml` are stored in `data/maven_projects`.
This step identifies 34 560 single module maven projects.

## 3. Download pom.xml files

The third step download the `pom.xml` file from Github for the single module maven projects that we identified in step 2.
The `pom.xml` files are stored in `data/poms`.
We downloaded 34 239 pom.xml files.

## 4. Download the Github details of the projects

This step requests the Github details of the projects such as the number of contributors, number of stars, ...
The details are stored in `data/repo_details`.
We stored the details for 34 280 projects.

## 5. Generate the dependency graph between the projects

In this step, we parse the pom downloaded in step 3 to identify the dependency links between the projects. The goal of this step is to identify the libraries and their clients.
The result of this step is stored in `data/maven_graph.json`.
We identify XXX libraries and XXX clients that use XXX different versions of the libraries.

## 6. Identify the commit for each version that the clients are using

The step identifies which commit contain the source code of the specific version for the libraries. 
For this step, we collect the list of tags for a given project using GitHub API and we also download the history of the ´pom.xml` in order to be able to extract the version of the libraries.
The result of this step is stored in `data/pom_commits`. `data/maven_graph_with_release.json` contains the information about `data/maven_graph.json` plus a map between a version and a commit. All the versions that we did not identify the associated commits are removed.
We downloaded the tag list for 155 libraries and 18 678 versions of the pom.xml.

## 7. Execute the test for the libraries

This step executes the test-suite 3 times for all the libraries from the previous step.
The result of the tests are stored in `data/maven_graph_with_test_results.json`
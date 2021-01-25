# Duets Dataset

# Structure
```
- README.md
- projects-list.txt
- scripts
  - <step>.js
  - stat.js
- dataset
  - dataset-info.json
  - <org>
    - <project>        
      - project-info.json
      - project-files.json
      - commits
        - <commit>
          - pom.xml
          - built.log
          - test-results
            - <test_result>.xml
          - jacoco.xml
```

# Format
```js
{
  "com.alibaba:fastjson": {
    "groupId": "com.alibaba",
    "artifactId": "fastjson",
    "repo_name": "alibaba/fastjson",
    "clients": {
      "1.2.46": [
        {
          "repo_name": "861763765/mqtt-demo",
          "groupId": "com.example.mqtt.demo", 
          "artifactId": "mqtt-demo",
          "version": "1.2.46",
          "commit": "4e704644e",
          "test_results": [
            { "error": 0, "failing": 0, "passing": 1, "execution_time": 0.525 },
            { "error": 0, "failing": 0, "passing": 1, "execution_time": 0.514 },
            { "error": 0, "failing": 0, "passing": 1, "execution_time": 0.75 }
          ]
        },
        ... // clients for the other releases
      ]
    },
    "releases": {
      "1.2.46": "00bbb28bf0",
      ... // commit sha for the other releases
    },
    "test_results": {
      "1.2.46": [
        {"passing": 4229, "failing": 0, "error": 0, "execution_time": 62.698},
        {"passing": 4229, "failing": 0, "error": 0, "execution_time": 62.755},
        {"passing": 4229, "failing": 0, "error": 0, "execution_time": 64.971}
      ],
      ... // test results for the other releases
    }
  },
  ... // other libraries
}
```

# Generate The dataset

The first step is to create the configuration file in `script/config.js`.
The file needs to contain the following information:
```js
module.exports = {
    "github_tokens": [], // the list of github tokens to collect data, the more the best
    output: __dirname + '/../data/' // where the data is stored
}
```

```bash
npm i;
node scripts/2.a.collect_project_files.js
node scripts/2.b.identify_single_module_projects.js
node scripts/2.c.get_project_details.js
node scripts/3.a.download_poms.js
node scripts/3.b.generate_dep_graph.js
node scripts/4.identify_commit_for_lib_releases.js
node scripts/5.a.test_libraries.js
node scripts/5.b.test_clients.js
node scripts/5.c.generate_final_dataset.js
```

# Creation Steps

## 0. List of Java projects

147 991 Java projects from Github that has more than 5 stars, the list of projects is available at `project_list.txt`.

## 1. List all the file from all the projects

This step takes the 147 991 Java projects from Github, uses the GitHub API to list all the files from the projects.
We succeed to collect the list of files for 147 840 projects.

## 2. Identify the single module maven projects

The second step identifies the single module maven projects. We look in the list of files collected in step 1 if the project contains only one `pom.xml`.
The output of this step in a JSON file for each single module project that contains the path of the `pom.xml`.
This step identifies 34 560 single module maven projects.

## 3. Download pom.xml files

The third step download the `pom.xml` file from Github for the single module maven projects that we identified in step 2.
We downloaded 34 239 pom.xml files.

## 4. Download the Github details of the projects

This step requests the Github details of the projects such as the number of contributors, number of stars, ...
We stored the details for 34 280 projects.

## 5. Generate the dependency graph between the projects

In this step, we parse the pom downloaded in step 3 to identify the dependency links between the projects. The goal of this step is to identify the libraries and their clients.
We identify XXX libraries and XXX clients that use XXX different versions of the libraries.

## 6. Identify the commit for each version that the clients are using

The step identifies which commit contain the source code of the specific version for the libraries. 
For this step, we collect the list of tags for a given project using GitHub API and we also download the history of the ´pom.xml` in order to be able to extract the version of the libraries.
All the versions that we did not identify the associated commits are removed.
We downloaded the tag list for 155 libraries and 18 678 versions of the pom.xml.

## 7. Execute the test for the libraries

This step executes the test-suite 3 times for all the libraries from the previous step.

## 8. Execute the test for the clients

This step executes the test-suite 3 times for all the libraries from the previous step.

## 9. Generating the final dataset

This last step generate the file that is located in `data/dataset-info.json`.
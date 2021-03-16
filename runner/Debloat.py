import subprocess
import os
import json
import sys, traceback
from core.Project import Project


class Debloat:
    def __init__(self, project: Project):
        self.project = project

    def inject_jdbl(self):
        self.project.reset_surefire_plugin()

        self.project.pom.add_plugin("se.kth.castor", "jdbl-maven-plugin", "1.0.0", [{
            "name": "executions",
            "children": [
                {
                    "name": "execution",
                    "children": [
                        {
                            "name": "goals",
                            "children": [
                                {
                                    "name": "goal",
                                    "text": "test-based-debloat"
                                }
                            ]
                        }
                    ]
                }
            ]
        }])

        self.project.pom.write_pom()
        pass

    def inject_DepClean(self):
        self.project.reset_surefire_plugin()

        self.project.pom.add_plugin("se.kth.castor", "depclean-maven-plugin", "1.1.0", [{
            "name": "executions",
            "children": [
                {
                    "name": "execution",
                    "children": [
                        {
                            "name": "goals",
                            "children": [
                                {
                                    "name": "goal",
                                    "text": "depclean"
                                }
                            ]
                        }
                    ]
                }
            ]
        }])

        self.project.pom.write_pom()
        pass

    def jdbl(self, stdout: str = None):
        self.inject_jdbl()
        return self.project.package(stdout=stdout)

    def depClean(self, stdout: str = None):
        maven_proxy = ''
        maven_proxy_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..", "maven-proxy.xml")
        if os.path.exists(maven_proxy_path):
            maven_proxy = '-gs %s' % (maven_proxy_path)

        cmd = 'cd %s; mvn %s se.kth.castor:depclean-maven-plugin:1.1.0:depclean -Dcreate.pom.debloated=true -Dcreate.result.json=true' % (
            self.project.path, maven_proxy)
        if stdout is not None:
            cmd += ' > %s 2>&1' % (stdout)
        try:
            output = subprocess.check_output(cmd, shell=True)
            output = output.decode("utf-8")

            path_json = os.path.join(self.project.path, "depclean-results.json")
            if os.path.exists(path_json):
                output = {
                    'usage': {},
                    'dependencies': {}
                }
                with open(path_json, 'r') as fd:
                    output['dependencies'] = json.load(fd)
                path_usage = os.path.join(self.project.path, "class-usage.csv")
                if os.path.exists(path_usage):
                    with open(path_usage, 'r', encoding="utf-8") as fd:
                        c = fd.read()
                        lines = c.split('\n')
                        for line in lines[1:]:
                            if len(line) == 0:
                                continue
                            (projectClass,dependencyClass,dependency) = line.split(',')
                            if projectClass not in output['usage']:
                                output['usage'][projectClass] = {}
                            if dependency not in output['usage'][projectClass]:
                                output['usage'][projectClass][dependency] = []
                            if dependencyClass not in output['usage'][projectClass][dependency]:
                                output['usage'][projectClass][dependency].append(dependencyClass)
                return output

            if stdout is not None:
                with open(stdout, 'r', encoding="utf-8", errors="surrogateescape") as fd:
                    output = fd.read()

            lines = output.split("\n")
            output = {
                "direct_dependencies": [],
                "transitive_dependencies": [],
                "used_artifacts": [],
                "used_direct_dependencies": [],
                "used_transitive_dependencies": [],
                "unused_direct_dependencies": [],
                "unused_transitive_dependencies": [],
            }
            debloat_report_started = False
            current = None
            for line in lines:
                if not debloat_report_started:
                    if "Starting DepClean dependency analysis" in line:
                        debloat_report_started = True
                    continue

                if "DIRECT DEPENDENCIES:" in line:
                    output["direct_dependencies"] = line.replace(
                        "DIRECT DEPENDENCIES: ", "").replace("[", "").replace("]", "").split(", ")
                    if output["direct_dependencies"][0] == '':
                        output["direct_dependencies"] = []
                elif "TRANSITIVE DEPENDENCIES: " in line:
                    output["transitive_dependencies"] = line.replace(
                        "TRANSITIVE DEPENDENCIES: ", "").replace("[", "").replace("]", "").split(", ")
                    if output["transitive_dependencies"][0] == '':
                        output["transitive_dependencies"] = []
                elif "USED ARTIFACTS:" in line:
                    output["used_artifacts"] = line.replace("USED ARTIFACTS:", "").replace(
                        "[", "").replace("]", "").split(", ")
                    if output["used_artifacts"][0] == '':
                        output["used_artifacts"] = []
                elif "Used direct dependencies" in line:
                    current = "used_direct_dependencies"
                elif "Used transitive dependencies" in line:
                    current = "used_transitive_dependencies"
                elif "Potentially unused direct dependencies" in line:
                    current = "unused_direct_dependencies"
                elif "Potentially unused transitive dependencies" in line:
                    current = "unused_transitive_dependencies"
                elif current is not None and len(line) > 1 and line[0] == "\t":
                    output[current].append(line.strip())
            return output
        except Exception as ex:
            print("[ERROR]", ex)
            traceback.print_exception(type(ex), ex, ex.__traceback__)
            return False

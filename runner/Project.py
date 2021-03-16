import subprocess
import traceback
import os
from github import Github
import xml.etree.ElementTree as xml

from PomExtractor import PomExtractor

token = None
if 'GITHUB_OAUTH' in os.environ and len(os.environ['GITHUB_OAUTH']) > 0:
    token = os.environ['GITHUB_OAUTH']
g = Github(token)


class Project:
    def __init__(self, url: str):
        self.url = url
        self.name = os.path.basename(url).replace(".git", '')
        self.repo = url.replace("https://github.com/", '').replace(".git", '')
        if self.repo[-1] == '/':
            self.repo = self.repo[:-1]
        self.path: str = None
        self.original_path: str = None
        self.pom: PomExtractor = None
        self.releases = []

    def clone(self, path: str):
        try:
            cmd = "cd %s;git clone -q --depth=1 %s;" % (path, self.url)
            subprocess.check_call(cmd, shell=True)
            self.path = os.path.join(path, self.name)
            self.original_path = os.path.join(path, self.name)
            self.pom = PomExtractor(self.path)
            self.path = os.path.dirname(self.pom.poms[0]['path'])
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def checkout_version(self, version: str):
        version = version.lower().replace('v.', '').replace(
            'v', '').replace('_', '.').replace('-', '.')
        releases = self.get_releases()
        for r in releases:
            v = r.name.lower().replace('v.', '').replace(
                'v', '').replace('_', '.').replace('-', '.')
            try:
                index = v.index(version)
                v = v[index:]
                temp_version = version.replace('_', '.').replace('-', '.')
                if len(v) > len(temp_version):
                    temp_version += '.0'
                if v == temp_version:
                    return self.checkout_commit(r.commit.sha)
            except ValueError:
                continue
            except Exception:
                traceback.print_stack()
                continue
        return False

    def checkout_commit(self, commit: str):
        try:
            cmd = 'cd %s; git fetch -q origin %s; git checkout -q %s' % (
                self.path, commit, commit)
            subprocess.check_call(cmd, shell=True)
            self.pom = PomExtractor(self.original_path)
            self.path = os.path.dirname(self.pom.poms[0]['path'])
            return True
        except:
            return False

    def get_commit(self):
        cmd = 'cd %s; git rev-parse HEAD' % (self.path)
        return subprocess.check_output(cmd, shell=True).decode('UTF-8').strip()

    def clean(self):
        cmd = 'cd %s;mvn clean -B;' % (self.path)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def dependency_tree(self):
        maven_proxy = ''
        maven_proxy_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "maven-proxy.xml")
        if os.path.exists(maven_proxy_path):
            maven_proxy = '-gs %s' % (maven_proxy_path)
        cmd = "cd %s; mvn %s dependency:tree -Dverbose=true -DoutputFile=dependency_tree.txt -q;cat dependency_tree.txt;rm dependency_tree.txt" % (self.path, maven_proxy)
        def get_index_artifact(line):
            index = 0
            while line[index] == ' ' or line[index] == '+' or line[index] == '|' or line[index] == '\\' or line[index] == '-':
                index += 1
            return index
        def extractArtifact(line):
            index = get_index_artifact(line)
            data = line[index:]
            output = {
                "artifactid": None,
                "groupid": None,
                "version": None,
                "package": None,
                "scope": None,
                "omitted": False,
                "omitted_reason": None
            }
            if " " in data:
                split = data.split(" ")
                data = split[0]
                if len(split) > 1:
                    if "version selected from constraint" in split[1]:
                        output['range'] = split[1].replace(
                            " (version selected from constraint ", "")[:-1]
                    elif "omitted" in line:
                        output['omitted'] = True
                        if "omitted for duplicate" in line:
                            output['omitted_reason'] = "duplicated"
                        elif "omitted for conflict" in line:
                            output['omitted_reason'] = "conflict"
                        else:
                            output['omitted_reason'] = "other"
                        data = data[1:]
            info = data.split(":")
            output['groupid'] = info[0]
            output['artifactid'] = info[1]
            output['package'] = info[2]
            output['version'] = info[3]
            if len(info) > 4:
                output['scope'] = info[4]
            return output
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        print(output)
        lines = output.split("\n")
        modules = []
        parent_artifact = None
        previous_artifact = None
        for line in lines:
            if len(line) == 0:
                continue
            level = 0
            if '-' in line[:get_index_artifact(line)]:
                level = get_index_artifact(line)
            artifact = extractArtifact(line)
            artifact['child'] = []
            artifact['level'] = level
            artifact['child_level'] = level + 3
            
            artifact['parent'] = parent_artifact
            if level == 0:
                parent_artifact = artifact
                modules.append(parent_artifact)
            
            if parent_artifact['child_level'] == level:
                parent_artifact['child'].append(artifact)
            elif parent_artifact['child_level'] < level:
                parent_artifact = previous_artifact
                artifact['parent'] = parent_artifact
                parent_artifact['child'].append(artifact)
            elif level != 0:
                while parent_artifact['child_level'] != level:
                    parent_artifact = parent_artifact['parent']
                parent_artifact['child'].append(artifact)
            previous_artifact = artifact

        def remove_parent(a):
            if 'parent' in a:
                del a['parent']
            if 'level' in a:
                del a['level']
            if 'child_level' in a:
                del a['child_level']
            for child in a['child']:
                remove_parent(child)

        for m in modules:
            remove_parent(m)
        return modules
        
    def classpath(self):
        maven_proxy = ''
        maven_proxy_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..","maven-proxy.xml")
        if os.path.exists(maven_proxy_path):
            maven_proxy = '-gs %s' % (maven_proxy_path)

        cmd = "cd %s; mvn %s dependency:build-classpath -Dscope=test;" % (
            self.path, maven_proxy)
        try:
            cp = []
            output = subprocess.check_output(cmd, shell=True).decode("utf-8")
            lines = output.split("\n")
            for line in lines:
                if len(line) == 0:
                    continue
                if line[0] != "/":
                    continue
                cp.append(line)
            return cp
        except Exception as e:
            print(e)
            return None

    def compile(self, clean: bool = True, stdout: str = None, timeout: str = None):
        clean_cmd = 'mvn clean -B -q > /dev/null; '
        if clean is False:
            clean_cmd = ''
        timeout_cmd = ''
        if timeout is not None:
            timeout_cmd = 'timeout -k 1m -s SIGKILL %s' % timeout
        maven_proxy = ''
        maven_proxy_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..","maven-proxy.xml")
        if os.path.exists(maven_proxy_path):
            maven_proxy = '-gs %s' % (maven_proxy_path)
        cmd = 'cd %s;%s%s mvn %s test -DskipTests -e -Dgpg.skip=true -B -Dmaven.javadoc.skip=true -Drat.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dlicense.skip=true -Dsource.skip=true' % (
            self.path, clean_cmd, timeout_cmd, maven_proxy)
        if stdout is not None:
            cmd += ' > %s 2>&1' % (stdout)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def test(self, clean: bool = True, stdout: str = None, timeout: str = None):
        clean_cmd = 'mvn clean -B -q > /dev/null ;'
        if clean is False:
            clean_cmd = ''
        timeout_cmd = ''
        if timeout is not None:
            timeout_cmd = 'timeout -k 1m -s SIGKILL %s' % timeout
        maven_proxy = ''
        maven_proxy_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..","maven-proxy.xml")
        if os.path.exists(maven_proxy_path):
            maven_proxy = '-gs %s' % (maven_proxy_path)
        cmd = 'cd %s;%s%s mvn %s test -DtrimStackTrace=false -e --fail-never -Dmaven.test.failure.ignore=true -B -Dmaven.javadoc.skip=true -Drat.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dlicense.skip=true -Dsource.skip=true' % (
            self.path, clean_cmd, timeout_cmd, maven_proxy)
        if stdout is not None:
            cmd += ' > %s 2>&1' % (stdout)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def get_test_results(self):
        output = {}

        for root, dirs, files in os.walk(self.path):
            for dir in dirs:
                if dir != "surefire-reports":
                    continue
                test_results_path = os.path.join(root, dir)
                for test in os.listdir(test_results_path):
                    if ".xml" not in test:
                        continue
                    test_path = os.path.join(test_results_path, test)
                    try:
                        test_results = xml.parse(test_path).getroot()
                        test_cases = test_results.findall("testcase")
                        for e in test_cases:
                            cl = e.get("classname")
                            if cl not in output:
                                cl_test = {
                                    'name': cl,
                                    'test_cases': []
                                }
                                if test_results.get('time') is not None:
                                    cl_test['execution_time'] = float(
                                        test_results.get('time'))
                                if test_results.get('errors') is not None:
                                    cl_test['error'] = int(
                                        test_results.get('errors'))
                                if test_results.get('failures') is not None:
                                    cl_test['failing'] = int(
                                        test_results.get('failures'))
                                if test_results.get('failed') is not None:
                                    cl_test['failing'] = int(
                                        test_results.get('failed'))
                                if test_results.get('tests') is not None:
                                    cl_test['passing'] = int(test_results.get(
                                        'tests')) - int(test_results.get('errors')) - int(test_results.get('failures'))
                                if test_results.get('passed') is not None:
                                    cl_test['passing'] = int(
                                        test_results.get('passed'))

                                output[cl] = cl_test
                            test_case = {
                                'name': e.get("name"),
                                'execution_time': float(e.get('time'))
                            }
                            error = e.find("error")
                            if error is not None:
                                test_case['error'] = {
                                    "message": error.get("message"),
                                    "type": error.get("type"),
                                    "error": error.text
                                }
                                pass

                            error = e.find("failure")
                            if error is not None:
                                test_case['failure'] = {
                                    "message": error.get("message"),
                                    "type": error.get("type"),
                                    "error": error.text
                                }

                            output[cl]['test_cases'].append(test_case)
                    except Exception as e:
                        print(e)
                        pass
        return output

    def install(self, stdout: str = None, timeout: str = None) -> bool:
        timeout_cmd = ''
        if timeout is not None:
            timeout_cmd = 'timeout -k 1m -s SIGKILL %s' % timeout
        maven_proxy = ''
        maven_proxy_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..","maven-proxy.xml")
        if os.path.exists(maven_proxy_path):
            maven_proxy = '-gs %s' % (maven_proxy_path)
        cmd = 'cd %s; %s mvn %s install -DskipTests -Dgpg.skip=true -Dmaven.test.error.ignore=true -Dmaven.test.failure.ignore=true -B -Dmaven.javadoc.skip=true -Drat.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dlicense.skip=true -Dsource.skip=true' % (
            self.path,
            timeout_cmd,
            maven_proxy)
        if stdout is not None:
            cmd += ' > %s 2>&1' % (stdout)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def package(self, stdout: str = None, timeout: str = None) -> bool:
        timeout_cmd = ''
        if timeout is not None:
            timeout_cmd = 'timeout -k 1m -s SIGKILL %s' % timeout
        maven_proxy = ''
        maven_proxy_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "..","maven-proxy.xml")
        if os.path.exists(maven_proxy_path):
            maven_proxy = '-gs %s' % (maven_proxy_path)
        cmd = 'cd %s; mvn clean -q -B;%s mvn %s package -e --fail-never -Dgpg.skip=true  -Dmaven.test.error.ignore=true -Dmaven.test.failure.ignore=true -B -Dmaven.javadoc.skip=true -Drat.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dlicense.skip=true -Dsource.skip=true' % (
            self.path,
            timeout_cmd,
            maven_proxy)
        if stdout is not None:
            cmd += ' > %s 2>&1' % (stdout)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def copy_jar(self, dst: str) -> bool:
        dst = os.path.abspath(dst)
        cmd = 'cd %s/target; cp *jar-with-dependencies.jar %s;' % (
            self.path, dst)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def copy_test_results(self, dst: str):
        dst = os.path.abspath(dst)
        if not os.path.exists(os.path.join(self.path, "target", "surefire-reports")):
            return False
        cmd = 'cd %s/target/; cp -r surefire-reports %s' % (self.path, dst)
        print(cmd)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def copy_jacoco(self, dst: str):
        dst = os.path.abspath(dst)
        cmd = 'cd %s/target/; cp -r site/jacoco/jacoco.xml %s; cp -r site/jacoco/jacoco.csv %s' % (
            self.path, dst, dst)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def copy_pom(self, dst: str):
        dst = os.path.abspath(dst)
        cmd = 'cd %s; cp -r %s %s' % (self.path, self.pom.poms[0]['path'], dst)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def copy_report(self, dst: str):
        dst = os.path.abspath(dst)
        cmd = f'cd {self.path}; mv .jdbl/*-debloated.jar .jdbl/debloat.jar; mv .jdbl/*-original.jar .jdbl/original.jar; cp -r .jdbl/* {dst};'
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

    def unzip_debloat(self, root: str, library: str, version: str, debloated: bool = True):
        # self.pom.remove_dependency(group_id, artifact_id)
        path_lib = os.path.join(root, library.repo.replace('/', '_'), version)
        path_jar = os.path.join(path_lib, "debloat", "dup.jar")
        if not os.path.exists(path_jar):
            path_jar = os.path.join(path_lib, "debloat", "debloat.jar")
        if not debloated:
            path_jar = os.path.join(path_lib, "original", "original.jar")

        cmd = "mkdir -p %s/target/classes/; cd %s/target/classes/; jar xf %s;" % (
            self.path, self.path, path_jar)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except Exception as e:
            traceback.print_stack()
            return False

    def inject_debloat_library(self, root: str, library: str, version: str, debloated: bool = True):
        path_lib = os.path.join(root, library.repo.replace('/', '_'), version)
        path_jar = os.path.join(path_lib, "debloat", "dup.jar")
        if not os.path.exists(path_jar):
            path_jar = os.path.join(path_lib, "debloat", "debloat.jar")
        if not debloated:
            path_jar = os.path.join(path_lib, "original", "original.jar")

        artifact_id = library.pom.get_artifact()
        group_id = library.pom.get_group()
        cmd = "cd %s; mvn install:install-file -Dfile=%s -DgroupId=%s -DartifactId=%s -Dversion=%s -Dpackaging=jar -B -Dmaven.javadoc.skip=true;" % (
            self.path, path_jar, group_id, artifact_id, version)
        try:
            subprocess.check_call(cmd, shell=True)
            return True
        except:
            return False

        # self.pom.change_depency_path(group_id, artifact_id, path_jar)
        # self.pom.write_pom()

    def reset_surefire_plugin(self):
        (includes, excludes, configuration) = self.pom.get_included_excluded_tests()
        conf = []
        exclude_config = []
        for exclude in excludes:
            exclude_config.append({
                "name": "exclude",
                "text": exclude
            })
        if len(exclude_config) > 0:
            conf.append({
                "name": "excludes",
                "children": exclude_config
            })
        include_config = []
        for include in includes:
            include_config.append({
                "name": "include",
                "text": include
            })
        if len(include_config) > 0:
            conf.append({
                "name": "includes",
                "children": include_config
            })
        if "testSourceDirectory" in configuration:
            conf.append({
                "name": "testSourceDirectory",
                "text": configuration["testSourceDirectory"]
            })
        if "testClassesDirectory" in configuration:
            conf.append({
                "name": "testClassesDirectory",
                "text": configuration["testClassesDirectory"]
            })
        if "test" in configuration:
            conf.append({
                "name": "test",
                "text": configuration["test"]
            })
        self.pom.add_plugin("org.apache.maven.plugins", "maven-surefire-plugin", "2.19.1", [{
            "name": "configuration",
            "children": conf
        }])
        self.pom.write_pom()

    def inject_jacoco_plugin(self):
        self.reset_surefire_plugin()
        self.pom.add_plugin("org.jacoco", "jacoco-maven-plugin", "0.8.5", [
            {
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
                                        "text": "prepare-agent"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "name": "execution",
                        "children": [
                            {
                                "name": "id",
                                "text": "report"
                            }, {
                                "name": "phase",
                                "text": "test"
                            }, {
                                "name": "goals",
                                "children": [{
                                    "name": "goal",
                                    "text": "report"
                                }]
                            }
                        ]
                    }
                ]
            }])
        self.pom.write_pom()
        return True

    def inject_assembly_plugin(self):
        self.pom.add_plugin(None, "maven-assembly-plugin", "3.2.0", [{
            "name": "executions",
            "children": [
                {
                    "name": "execution",
                    "children": [
                        {
                            "name": "phase",
                            "text": "package"
                        },
                        {
                            "name": "goals",
                            "children": [
                                {
                                    "name": "goal",
                                    "text": "single"
                                }
                            ]
                        }
                    ]
                }]
        }, {
            "name": "configuration",
            "children": [
                    {
                        "name": "descriptorRefs",
                        "children": [
                            {
                                "name": "descriptorRef",
                                "text": "jar-with-dependencies"
                            }
                        ]
                    }
            ]
        }
        ])
        self.pom.write_pom()
        return True

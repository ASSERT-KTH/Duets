import xml.etree.ElementTree as xml
from xml.etree.ElementTree import Element, SubElement, tostring

from pathlib import Path


def stripNs(el):
  '''Recursively search this element tree, removing namespaces.'''
  if el.tag.startswith("{"):
    el.tag = el.tag.split('}', 1)[1]  # strip namespace
  for k in list(el.attrib):
    if k.startswith("{"):
      k2 = k.split('}', 1)[1]
      el.attrib[k2] = el.attrib[k]
      del el.attrib[k]
  for child in el:
    stripNs(child)


def clean_value(text: str):
    return text.replace("\n", "").replace("\t", "").replace(" ", "")


def indent(elem: Element, level=0, more_sibs=False):
    i = "\n"
    if level:
        i += (level-1) * '  '
    num_kids = len(elem)
    if num_kids:
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
            if level:
                elem.text += '  '
        count = 0
        for kid in elem:
            indent(kid, level+1, count < num_kids - 1)
            count += 1
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
            if more_sibs:
                elem.tail += '  '
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
            if more_sibs:
                elem.tail += '  '


class PomExtractor:
    def __init__(self, path: str):
        self.namespaces = {'xmlns': 'http://maven.apache.org/POM/4.0.0'}
        self.path = path
        self.poms = []
        for p in Path(path).rglob('pom.xml'):
            f = xml.parse(p)
            root = f.getroot()
            stripNs(root)
            if root.attrib.get('schemaLocation') is not None:
                root.attrib.pop('schemaLocation')
            self.poms.append({"path": p, "root": root})

    def write_pom(self):
        for pom in self.poms:
            indent(pom["root"])
            rough_string = tostring(
                pom["root"], encoding="UTF-8").decode().replace("ns0:", '')
            with open(pom["path"], 'w') as fd:
                fd.write(rough_string)

    def get_artifact(self) -> str:
        r = self.poms[0]["root"].find('artifactId')
        if r is not None:
            return clean_value(r.text)
        r = self.poms[0]["root"].find('parent')
        if r is not None:
            r = r.find('artifactId')
            if r is not None:
                return clean_value(r.text)
        return ''

    def get_group(self) -> str:
        r = self.poms[0]["root"].find('groupId')
        if r is not None:
            return clean_value(r.text)
        r = self.poms[0]["root"].find('parent')
        if r is not None:
            r = r.find('groupId')
            if r is not None:
                return clean_value(r.text)
        return ''

    def get_version(self) -> str:
        r = self.poms[0]["root"].find("version")
        if r is not None:
            return clean_value(r.text)
        r = self.poms[0]["root"].findall('*//version')[0]
        if r is not None:
            return clean_value(r.text)
        return ''

    def remove_dependency(self, group_id: str, artifact_id: str) -> str:
        for pom in self.poms:
            prop_parents = self.poms[0]["root"].findall('*//dependency/..')
            for parent in prop_parents:
                for dep in parent:
                    gr = dep.find('groupId')
                    if gr is not None:
                        gr = clean_value(gr.text)
                    if group_id != gr:
                        continue
                    ar = dep.find('artifactId')
                    if ar is not None:
                        ar = clean_value(ar.text)
                    if ar != artifact_id:
                        continue
                    parent.remove(dep)
                    return dep
        return None

    def get_version_dependency(self, group_id: str, artifact_id: str) -> str:
        for pom in self.poms:
            deps = pom["root"].findall('*//dependency')
            for dep in deps:
                gr = clean_value(dep.find('groupId').text)
                ar = clean_value(dep.find('artifactId').text)
                if gr == group_id and ar == artifact_id:
                    version = dep.find('version')
                    if version is not None:
                        version = clean_value(version.text)
                    return version
        return None

    def change_depency_path(self, group_id: str, artifact_id: str, path: str) -> bool:
        for pom in self.poms:
            deps = pom["root"].findall('*//dependency')
            for dep in deps:
                gr = clean_value(dep.find('groupId').text)
                ar = clean_value(dep.find('artifactId').text)
                if gr == group_id and ar == artifact_id:
                    scope = dep.find('scope')
                    if scope is None:
                        scope = SubElement(dep, "scope")
                    scope.text = "system"
                    SubElement(dep, "systemPath").text = path
                    return True
        return False

    def get_included_excluded_tests(self) -> (str, str):
        excludes = []
        includes = []
        configuration = {}
        x: Element = self.poms[0]["root"]
        prop_parents = x.findall('*//plugin/..')
        group_id = 'org.apache.maven.plugins'
        artifact_id = 'maven-surefire-plugin'
        for parent in prop_parents:
            for declared_plugin in parent:
                gr = declared_plugin.find('groupId')
                if gr is not None:
                    gr = clean_value(gr.text)
                if group_id != gr:
                    continue
                ar = declared_plugin.find('artifactId')
                if ar is not None:
                    ar = clean_value(ar.text)
                if ar != artifact_id:
                    continue
                for exclude in declared_plugin.findall('*//exclude'):
                    excludes.append(exclude.text)
                for include in declared_plugin.findall('*//include'):
                    includes.append(include.text)
                conf: Element = declared_plugin.find('configuration')
                if conf is not None:
                    for a in conf.getchildren():
                        configuration[a.tag] = a.text
        return (includes, excludes, configuration)

    def remove_plugin(self, group_id: str, artifact_id: str):
        prop_parents = self.poms[0]["root"].findall('*//plugin/..')
        for parent in prop_parents:
            for declared_plugin in parent:
                gr = declared_plugin.find('groupId')
                if gr is not None:
                    gr = clean_value(gr.text)
                if group_id != gr:
                    continue
                ar = declared_plugin.find('artifactId')
                if ar is not None:
                    ar = clean_value(ar.text)
                if ar != artifact_id:
                    continue
                # the plugin is the same remove it
                parent.remove(declared_plugin)

    def add_dependency(self, group_id: str, artifact_id: str, version: str, scope: str = None):
        # check if plugin is already defined if yes, remove it
        self.remove_dependency(group_id, artifact_id)

        build_section = None
        dependencies_section = self.poms[0]["root"].find('dependencies')
        if dependencies_section is None:
            # create build section
            dependencies_section = SubElement(
                self.poms[0]["root"], 'dependencies')

        new_dependency = SubElement(dependencies_section, 'dependency')
        if group_id is not None:
            SubElement(new_dependency, 'groupId').text = group_id
        SubElement(new_dependency, 'artifactId').text = artifact_id
        SubElement(new_dependency, 'version').text = version
        if scope is not None:
            SubElement(new_dependency, 'scope').text = scope

    def add_plugin(self, group_id: str, artifact_id: str, version: str, config: []) -> {}:
        # check if plugin is already defined if yes, remove it
        self.remove_plugin(group_id, artifact_id)

        build_section = None
        plugins_section = None
        build = self.poms[0]["root"].findall('build')
        if len(build) == 0:
            # create build section
            build_section = SubElement(self.poms[0]["root"], 'build')

            # create plugin section
            plugins_section = SubElement(build_section, 'plugins')
        else:
            build_section = build[0]
            plugins_section = build_section.find('plugins')
            if plugins_section is None:
                plugins_section = SubElement(build_section, 'plugins')

        new_plugin = SubElement(plugins_section, 'plugin')
        if group_id is not None:
            SubElement(new_plugin, 'groupId').text = group_id
        SubElement(new_plugin, 'artifactId').text = artifact_id
        SubElement(new_plugin, 'version').text = version

        def insert_config(parent, element):
            n = SubElement(parent, element['name'])
            if 'text' in element:
                n.text = element['text']
            elif 'children' in e:
                for c in element['children']:
                    insert_config(n, c)
        for e in config:
            insert_config(new_plugin, e)

        return self.poms[0]

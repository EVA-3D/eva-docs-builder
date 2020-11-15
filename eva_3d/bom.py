import csv
from pprint import pprint
from pathlib import Path

def define_env(env):

    env.variables.download_url = f'{env.conf["repo_url"]}/archive/{env.conf["version"]}.zip'

    def generate_bom_table(reader, indent_str=""):
        for index, row in enumerate(reader):
            yield "{}| {} |".format(indent_str, " | ".join(row))
            if index == 0:
                yield "{}| {} |".format(indent_str, " | ".join(["-" * len(col) for col in row]))

    @env.macro
    def bom(file_name, indent=0):
        indent_str = " " * indent
        with open(Path(env.project_dir) / "bom" / file_name, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            return "\n".join(generate_bom_table(reader, indent_str))

    @env.macro
    def eva_link(name):
        return f'[:octicons-mark-github-16: EVA 2 / {name}]({env.conf["eva_links"][name.lower()]})'

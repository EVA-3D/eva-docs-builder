import csv
from pprint import pprint
from pathlib import Path


def define_env(env):

    env.variables.download_url = (
        f'{env.conf["repo_url"]}/archive/{env.conf["version"]}.zip'
    )
    # import ipdb; ipdb.set_trace()

    def generate_bom_table(reader, indent_str=""):
        for index, row in enumerate(reader):
            if index != 0:
                if row[3].upper() == "PETG":
                    row[2] = f"[{row[2]}](stls/{row[2]}.stl)"
                    row[3] = "Yes"
                else:
                    row[3] = ""
            if index == 0:
                row[3] = "Printable"
            yield "{}| {} |".format(indent_str, " | ".join(row))
            if index == 0:
                yield "{}| {} |".format(
                    indent_str, " | ".join(["-" * len(col) for col in row])
                )

    @env.macro
    def bom(file_path: str, indent=0):
        indent_str = " " * indent
        with open(Path(env.conf["docs_dir"]) / file_path, newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=",", quotechar='"')
            return "\n".join(generate_bom_table(reader, indent_str))

    @env.macro
    def eva_link(name):
        return f'[:octicons-mark-github-16: EVA 2 / {name}]({env.conf["eva_links"][name.lower()]})'

    @env.macro
    def eva_download_button(name):
        return f'[Download :octicons-download-24:]({env.conf["eva_links"][name.lower()]}/archive/main.zip){{: .md-button .md-button--primary }}'
        

    @env.macro
    def onshape_link(name):
        return f'[:octicons-file-binary-24: Onshape: {name}]({env.conf["onshape"][name.lower()]})'

    @env.macro
    def doc_env():
        return {
            name: getattr(env, name) for name in dir(env) if not name.startswith("_")
        }

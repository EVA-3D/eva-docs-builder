import csv
import json
from pathlib import Path

from jinja2 import Environment, Markup
from mkdocs.plugins import BasePlugin

from eva_3d.models import get_page_meta, ItemEntry, Bom
from eva_3d.unpacker import Unpacker


BADGE_CSS_CLASSES = {
    "OFFICIAL": "",
    "CONTRIB": "contrib",
    "DEPRECATED": "deprecated",
}


class EVAPlugin(BasePlugin):
    def on_config(self, config):
        self.context = {}
        self.env = Environment()
        self.bom_cache = {}
        self.unpacker = Unpacker()

    def _get_context(self, page, config):
        return {
            "meta": page.meta,
            "config": config,
            "eva_download_button": self.get_download_button,
            "bom_to_md_table": self.bom_to_md_table,
            "bom_to_json": self.bom_to_json,
            "box": self.box(),
            **self.context,
        }

    def _generate_bom(self, file_path: str) -> Bom:
        if not file_path in self.bom_cache:
            parts = []
            page_src_path = Path(self.page.file.abs_src_path)
            with open(page_src_path.parent / "bom" / file_path, newline="") as csvfile:
                for row in csv.DictReader(csvfile, delimiter=",", quotechar='"'):
                    item = ItemEntry(
                        name=row["Name"],
                        qty=row["Quantity"],
                        material=row["Material"],
                    )
                    if item.type == "printable":
                        item.url = f"/stls/{row['Name']}.stl"
                    parts.append(item)
            self.bom_cache[file_path] = Bom(
                parts=parts,
                satisfies=self.page.meta.satisfies or [],
                type=self.page.meta.type,
            )

        return self.bom_cache[file_path]

    def _generate_bom_table(self, bom, indent_str=""):
        for index, item in enumerate(bom.parts):
            if index == 0:
                yield f"| Item | Quantity | Name | Type |"
                yield "{}| {} |".format(
                    indent_str, " | ".join(["-" * len(str(col)) for col in range(4)])
                )
            if item.url:
                yield f"{indent_str}| {index + 1} | {item.qty} | [{item.name}]({item.url}) | {item.type} |"
            else:
                yield f"{indent_str}| {index + 1} | {item.qty} | {item.name} | {item.type} |"

    def bom_to_md_table(self, file_path: str, indent=0):
        bom = self._generate_bom(file_path=file_path)
        return "\n".join(self._generate_bom_table(bom, " " * indent))

    def bom_to_json(self, file_path: str):
        bom = self._generate_bom(file_path=file_path)
        return json.dumps(bom.dict())

    def box(self):
        return Markup(
            '<a class="md-button md-button--primary">{% include ".icons/fontawesome/solid/truck-loading.svg" %}</a>'
        )

    def get_download_button(self):
        if not self.page.meta.repo_url:
            raise Exception("repo_url meta missing")
        return f"[Download :octicons-download-24:]({self.page.meta.repo_url}/archive/main.zip){{: .md-button .md-button--primary }}"

    def render(self, markdown, page, config):
        md_template = self.env.from_string(markdown)
        return md_template.render(**self._get_context(page, config))

    def on_page_markdown(self, markdown, page, config, files):
        self.unpacker.add_page(page)
        self.page = page
        self.page.meta = get_page_meta(page)
        self.config = config
        return self.render(markdown, page, config)

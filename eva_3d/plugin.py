import logging
from functools import partial
import json
from pathlib import Path
from typing import Optional

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.exceptions import PluginError
from pydantic.utils import import_string
from slugify import slugify
from sqlmodel import Session, select
from PIL import Image

from eva_3d import db
from eva_3d.utils import escapeb64, read_source


BADGE_CSS_CLASSES = {
    "OFFICIAL": "",
    "CONTRIB": "contrib",
    "DEPRECATED": "deprecated",
}


log = logging.getLogger("mkdocs.plugins")


class EVAPlugin(BasePlugin):

    config_scheme = (
        ("version", config_options.Type(str)),
        (
            "meta_model_class",
            config_options.Type(str, default="eva_3d.models.BasePageMeta"),
        ),
    )

    def on_config(self, config):
        self.context = {}
        config["version"] = self.config["version"]
        self.session = Session(db.engine)
        db.create_db_and_tables()
        self.pages = []
        self.env = config["theme"].get_env()
        self.env.filters["b64encode"] = escapeb64
        self.env.filters["bom_json"] = self.bom_json
        self.env.filters["md_table"] = self.md_table
        self.env.filters["yes_no"] = self.yes_no
        self.env.filters["slugify"] = slugify

        try:
            config["meta_model_class"] = import_string(self.config["meta_model_class"])
        except ImportError as exc:
            raise PluginError(
                f"Meta Model Class {self.config['meta_model_class']} could not be imported. {exc}"
            ) from exc

        return config

    def on_pre_page(self, page, config, files):
        page.read_source = partial(read_source, page)
        return page

    def bom_json(self, bom_table: db.BOMTable):
        return json.dumps(bom_table.dict())

    @staticmethod
    def yes_no(value: bool):
        return "yes" if value else "no"

    def md_table(self, bom_table: db.BOMTable, indent: int = 0):
        if not isinstance(bom_table, db.BOMTable):
            return ""
        indent_str = " " * indent
        rows = []
        for index, item in enumerate(bom_table.items):
            if index == 0:
                rows.append(f"| Item | Quantity | Name | Printable |")
                rows.append(
                    "{}| {} |".format(
                        indent_str,
                        " | ".join(["-" * len(str(col)) for col in range(4)]),
                    )
                )
            if item.is_printable:
                rows.append(
                    f"{indent_str}| {index + 1} | {item.quantity} | [{item.name}](/{self.page.url}stls/{item.name}.stl) | {self.yes_no(item.is_printable)} |"
                )
            else:
                rows.append(
                    f"{indent_str}| {index + 1} | {item.quantity} | {item.name} | {self.yes_no(item.is_printable)} |"
                )
        return "\n".join(rows)

    def add_page(self, page):
        if page not in self.pages:
            self.pages.append(page)

    def _get_markdown_context(self, page, config):
        return {
            "meta": page.meta,
            "eva": page.eva,
            "config": config,
            "cad_link": self.cad_link,
            "button": self.button,
            "get_bom": self.get_bom,
            "icon": self.get_icon,
            "crop": self.crop,
            **self.context,
        }

    def get_icon(self, icon_name: str) -> str:
        path = "/".join(icon_name.split("-", 2))
        icon = self.env.loader.load(self.env, f".icons/{path}.svg").render()
        return f'<i class="twemoji">{icon}</i>'

    def button(
        self,
        title: str,
        href: str,
        icon: Optional[str] = None,
        open_in_new_tab: bool = False,
    ):
        target = ""
        if open_in_new_tab:
            target = "target='_blank'"

        if icon:
            icon = f"{icon} "
        else:
            icon = ""

        return f"[{icon}{title}]({href}){{: .md-button .md-button--primary {target}}}"

    @property
    def cad_link(self):
        if not self.page.eva.onshape:
            return ""
        return self.button(
            "CAD",
            self.page.eva.onshape.cad_url,
            ":fontawesome-solid-file-import:",
            True,
        )

    def get_bom(self, page_uid=None):
        if page_uid is None:
            page_uid = self.page.eva.onshape.uid
        stmt = (
            select(db.BOMTable, db.BOMItem)
            .where(db.BOMItem.bom_table_id == db.BOMTable.id)
            .where(db.BOMTable.name == page_uid)
        )
        first = self.session.exec(stmt).first()
        if first:
            return first[0]

    def render_markdown(self, markdown, page, config):
        md_template = self.env.from_string(markdown)
        return md_template.render(**self._get_markdown_context(page, config))

    def crop(self, image_url: str, left: int, upper: int, right: int, lower: int):
        page_path = Path(self.page.file.src_path)
        image_path = Path(self.config["docs_dir"]) / page_path.parent / Path(image_url)
        new_image_path = (
            image_path.parent
            / f"{image_path.stem}_crop_{left}x{upper}x{right}x{lower}{image_path.suffix}"
        )
        if not new_image_path.exists():
            Image.open(image_path).crop((left, upper, right, lower)).save(
                new_image_path
            )
        return str(Path(image_url).parent / new_image_path.name)

    def on_page_markdown(self, markdown, page, config, files):
        self.add_page(page)
        self.page = page
        self.config = config
        return self.render_markdown(markdown, page, config)

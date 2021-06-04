import sys
import csv
import hashlib
import logging
from pathlib import Path
import shutil

from jinja2 import Environment, FileSystemLoader
from mkdocs.plugins import BasePlugin

from eva_3d.models import get_page_meta, ItemEntry, Bom
from eva_3d.unpacker import Unpacker
from eva_3d.utils import escapeb64
from eva_3d.db import get_db_connection, initialize_db, get_superbom, get_vendor_superbom, truncate_vendor_mapping
from eva_3d.bom import BOMLoader


BADGE_CSS_CLASSES = {
    "OFFICIAL": "",
    "CONTRIB": "contrib",
    "DEPRECATED": "deprecated",
}


log = logging.getLogger('mkdocs.plugins')

class EVAPlugin(BasePlugin):
    def on_config(self, config):
        self.context = {}
        self.env = Environment(loader=FileSystemLoader(config["theme"].dirs))
        self.env.filters["b64encode"] = escapeb64
        self.unpacker = Unpacker()

        self.db_conn = get_db_connection()
        initialize_db(self.db_conn)

        self.bom_loader = BOMLoader(self.db_conn)

    def _get_markdown_context(self, page, config):
        return {
            "meta": page.meta,
            "config": config,
            "download_button": self.download_button,
            "cad_link": self.cad_link,
            "get_bom": self.get_bom,
            "icon": self.get_icon,
            **self.context,
        }

    def get_icon(self, icon_name: str) -> str:
        path = "/".join(icon_name.split("-", 2))
        icon = self.env.loader.load(self.env, f".icons/{path}.svg").render()
        return f'<i class="twemoji">{icon}</i>'

    def get_cache_key(self, file_path):
        return hashlib.sha256(f"{self.page}:{file_path}".encode()).hexdigest()

    @property
    def cad_link(self):
        if not self.page.meta.cad_url:
            return ""
        return f"[:fontawesome-solid-file-import: CAD]({self.page.meta.cad_url}){{: .md-button .md-button--primary target='_blank'}}"

    @property
    def download_button(self):
        if not self.page.meta.repo_url:
            return ""
        return f"[:octicons-download-24: Download]({self.page.meta.repo_url}/archive/main.zip){{: .md-button .md-button--primary }}"

    def get_bom(self, bom_source_id):
        return self.page.boms_cache[bom_source_id]

    def render_markdown(self, markdown, page, config):
        md_template = self.env.from_string(markdown)
        return md_template.render(**self._get_markdown_context(page, config))

    def on_page_markdown(self, markdown, page, config, files):
        self.unpacker.add_page(page)
        self.page = page
        self.page.meta = get_page_meta(page)
        self.config = config
        self.page.boms_cache = {}
        for bom in self.page.meta.boms:
            rows = self.bom_loader.load_bom(
                Path(self.page.file.abs_src_path).parent / bom.source, bom.namespace
            )
            self.page.boms_cache[bom.id] = Bom(
                parts=[
                    ItemEntry(
                        name=item[0],
                        qty=item[1],
                        material=item[2],
                        url=item[3],
                    )
                    for item in rows
                ],
                satisfies=self.page.meta.satisfies or [],
                type=self.page.meta.type,
                cad_url=self.page.meta.cad_url,
            )
        return self.render_markdown(markdown, page, config)

    def on_post_build(self, config):
        with open(Path(config["docs_dir"]).parent / "vendors" / "template_superbom.csv", 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=",", quotechar='"')
            writer.writerow(["namespace", "eva_part_name", "qty", "type", "vendor_part_name", "vendor_sku", "vendor_ignore"])
            rows = get_superbom(self.db_conn)
            for row in rows:
                writer.writerow(list(row[0:4]) + ["", "", ""])

        try:
            vendors = config["vendors"]
        except KeyError:
            log.error("'vendors' key missing from config")
            sys.exit(1)

        for vendor in vendors:
            self.bom_loader.load_vendor_mapping(
                Path(config["docs_dir"]).parent / vendor["mapping_file"], vendor["name"]
            )
            with open(Path(config["docs_dir"]).parent / vendor["out_file"], 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=",", quotechar='"')
                writer.writerow(["namespace", "eva_part_name", "qty", "type", "vendor_part_name", "vendor_sku"])
                rows = get_vendor_superbom(self.db_conn, vendor["name"])
                for row in rows:
                    writer.writerow(row)
            truncate_vendor_mapping(self.db_conn)

        all_stls = Path(config["docs_dir"]).parent / "stls"
        shutil.copytree(all_stls, Path(config["site_dir"]) / "stls")

import hashlib
import logging
import json 

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from sqlmodel import Session, select

from eva_3d import db
from eva_3d.models import get_page_meta
from eva_3d.utils import escapeb64
from eva_3d.downloader import Downloader


BADGE_CSS_CLASSES = {
    "OFFICIAL": "",
    "CONTRIB": "contrib",
    "DEPRECATED": "deprecated",
}


log = logging.getLogger('mkdocs.plugins')

class EVAPlugin(BasePlugin):

    config_scheme = (
        ('version', config_options.Type(str)),
    )

    def on_config(self, config):
        self.context = {}
        config["version"] = self.config["version"]
        self.session = Session(db.engine)
        db.create_db_and_tables()
        self.pages = []
        self.env = config['theme'].get_env()
        self.env.filters["b64encode"] = escapeb64
        self.env.filters["bom_json"] = self.bom_json
        self.env.filters["md_table"] = self.md_table
        self.env.filters["yes_no"] = self.yes_no
        self.env.filters["safe_filename"] = Downloader.safe_filename

        return config
    
    def bom_json(self, bom_table: db.BOMTable):
        return json.dumps(bom_table.dict())

    @staticmethod
    def yes_no(value: bool):
        return "yes" if value else "no"

    def md_table(self, bom_table: db.BOMTable, indent: int = 0):
        if not bom_table:
            return ""
        indent_str = " " * indent
        rows = []
        for index, item in enumerate(bom_table.items):
            if index == 0:
                rows.append(f"| Item | Quantity | Name | Printable |")
                rows.append("{}| {} |".format(
                    indent_str, " | ".join(["-" * len(str(col)) for col in range(4)])
                ))
            if item.is_printable:
                rows.append(f"{indent_str}| {index + 1} | {item.quantity} | [{item.name}](/{self.page.url}stls/{item.name}.stl) | {self.yes_no(item.is_printable)} |")
            else:
                rows.append(f"{indent_str}| {index + 1} | {item.quantity} | {item.name} | {self.yes_no(item.is_printable)} |")
        return "\n".join(rows)

    def add_page(self, page):
        if page not in self.pages:
            self.pages.append(page)

    def _get_markdown_context(self, page, config):
        return {
            "meta": page.eva,
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
        if not self.page.eva.cad_url:
            return ""
        return f"[:fontawesome-solid-file-import: CAD]({self.page.eva.cad_url}){{: .md-button .md-button--primary target='_blank'}}"

    @property
    def download_button(self):
        if not self.page.eva.repo_url:
            return ""
        return f"[:octicons-download-24: Download]({self.page.eva.repo_url}/archive/main.zip){{: .md-button .md-button--primary }}"

    def get_bom(self):
        stmt = select(db.BOMTable, db.BOMItem).where(db.BOMItem.bom_table_id == db.BOMTable.id).where(db.BOMTable.name == self.page.eva.uid)
        first = self.session.exec(stmt).first()
        if first:
            return first[0]

    def render_markdown(self, markdown, page, config):
        md_template = self.env.from_string(markdown)
        return md_template.render(**self._get_markdown_context(page, config))

    def on_page_markdown(self, markdown, page, config, files):
        self.add_page(page)
        # self.unpacker.add_page(page)
        self.page = page
        self.page.eva = get_page_meta(page)
        self.config = config
        # self.page.boms_cache = {}
        # for bom in self.page.eva.boms:
        #     rows = self.bom_loader.load_bom(
        #         Path(self.page.file.abs_src_path).parent / bom.source, bom.namespace
        #     )
        #     self.page.boms_cache[bom.id] = Bom(
        #         parts=[
        #             ItemEntry(
        #                 name=item[0],
        #                 qty=item[1],
        #                 material=item[2],
        #                 url=item[3],
        #             )
        #             for item in rows
        #         ],
        #         satisfies=self.page.eva.satisfies or [],
        #         type=self.page.eva.type,
        #         cad_url=self.page.eva.cad_url,
        #     )
        return self.render_markdown(markdown, page, config)

    # def on_post_build(self, config):
    #     with open(Path(config["docs_dir"]).parent / "vendors" / "template_superbom.csv", 'w', newline='') as csvfile:
    #         writer = csv.writer(csvfile, delimiter=",", quotechar='"')
    #         writer.writerow(["namespace", "eva_part_name", "qty", "type", "vendor_part_name", "vendor_sku", "vendor_ignore"])
    #         rows = get_superbom(self.db_conn)
    #         for row in rows:
    #             writer.writerow(list(row[0:4]) + ["", "", ""])

    #     try:
    #         vendors = config["vendors"]
    #     except KeyError:
    #         log.error("'vendors' key missing from config")
    #         sys.exit(1)

    #     for vendor in vendors:
    #         self.bom_loader.load_vendor_mapping(
    #             Path(config["docs_dir"]).parent / vendor["mapping_file"], vendor["name"]
    #         )
    #         with open(Path(config["docs_dir"]).parent / vendor["out_file"], 'w', newline='') as csvfile:
    #             writer = csv.writer(csvfile, delimiter=",", quotechar='"')
    #             writer.writerow(["namespace", "eva_part_name", "qty", "type", "vendor_part_name", "vendor_sku"])
    #             rows = get_vendor_superbom(self.db_conn, vendor["name"])
    #             for row in rows:
    #                 writer.writerow(row)
    #         truncate_vendor_mapping(self.db_conn)

    #     all_stls = Path(config["docs_dir"]).parent / "stls"
    #     shutil.copytree(all_stls, Path(config["site_dir"]) / "stls")

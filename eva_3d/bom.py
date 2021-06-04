import csv
from pathlib import Path

from eva_3d.models import Bom, ItemEntry
from eva_3d.db import create_bom, create_item_entry, get_items_by_bom_id, create_vendor_mapping


class BOMLoader:

    def __init__(self, db_conn):
        self.db_conn = db_conn


    def load_bom(self, file_path, namespace):
        bom_id = create_bom(self.db_conn, file_path=str(file_path), namespace=namespace)
        with open(file_path, newline="") as csvfile:
            for row in csv.DictReader(csvfile, delimiter=",", quotechar='"'):
                url = None
                material = row["Material"].lower()
                item_type = "hardware"
                if material == "petg":
                    item_type = "printable"
                if item_type == "printable":
                    url = f"/stls/{row['Name']}.stl"
                create_item_entry(
                    self.db_conn, 
                    bom_id=bom_id,
                    name=row["Name"].strip(),
                    qty=int(row["Quantity"]),
                    type=item_type,
                    url=url
                )

        return get_items_by_bom_id(self.db_conn, bom_id)

    def load_vendor_mapping(self, file_path, vendor_name):
        with open(file_path, newline="") as csvfile:
            for row in csv.DictReader(csvfile, delimiter=",", quotechar='"'):
                create_vendor_mapping(
                    self.db_conn,
                    vendor_name,
                    row["eva_part_name"],
                    row["eva_part_type"],
                    row["vendor_part_name"],
                    row["vendor_sku"],
                    row["vendor_ignore"],
                )

    # def _generate_bom(self, file_path: str) -> Bom:
    #     cache_key = self.get_cache_key(file_path)
    #     if not cache_key in self.bom_cache:
    #         parts = {}
    #         page_src_path = Path(self.page.file.abs_src_path)
    #         with open(page_src_path.parent / "bom" / file_path, newline="") as csvfile:
    #             for row in csv.DictReader(csvfile, delimiter=",", quotechar='"'):
    #                 item = ItemEntry(
    #                     name=row["Name"].strip(),
    #                     qty=row["Quantity"],
    #                     material=row["Material"],
    #                 )
    #                 if item.type == "printable":
    #                     item.url = f"/stls/{row['Name']}.stl"
    #                 if item.name in parts:
    #                     parts[item.name].qty += item.qty
    #                 else:
    #                     parts[item.name] = item

    #         self.bom_cache[cache_key] = Bom(
    #             parts=list(parts.values()),
    #             satisfies=self.page.meta.satisfies or [],
    #             type=self.page.meta.type,
    #             cad_url=self.page.meta.cad_url,
    #         )

    #     return self.bom_cache[cache_key]

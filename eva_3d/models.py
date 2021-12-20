import json
from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, ValidationError
from slugify import slugify

from eva_3d.utils import PropertyBaseModel


class Satisfies(str, Enum):
    drive = "drive"
    hotend = "hotend"
    endstop = "endstop"
    bed_probe = "bed_probe"


class BomSource(BaseModel):
    id: str
    source: str
    namespace: str


class PageMeta(BaseModel):
    title: str
    satisfies: List[str]
    spec: Optional[str]
    type: Optional[str] = ""
    uid: Optional[str]
    badges: Optional[List[str]]
    contributors: Optional[List[str]]
    repo_url: Optional[Optional[str]]
    cad_url: Optional[Optional[str]]
    satisfies: Optional[List[Satisfies]]
    hide: Optional[List[str]]
    boms: Optional[List[BomSource]] = []
    usage: Optional[float]

    @property
    def percentage(self):
        return f"{self.usage * 100} %"


class ItemEntry(PropertyBaseModel):
    name: str
    qty: int
    material: str
    url: Optional[str]

    @property
    def type(self):
        return "printable" if self.material.lower() == "petg" else "hardware"

    @property
    def slug(self):
        return slugify(self.name)

class Bom(BaseModel):
    parts: List[ItemEntry]
    type: str
    satisfies: List[Satisfies]
    cad_url: Optional[str] = None

    def json(self):
        return json.dumps(self.dict())

    def md_table(self, indent: int):
        indent_str = " " * indent
        rows = []
        for index, item in enumerate(self.parts):
            if index == 0:
                rows.append(f"| Item | Quantity | Name | Type |")
                rows.append("{}| {} |".format(
                    indent_str, " | ".join(["-" * len(str(col)) for col in range(4)])
                ))
            if item.url:
                rows.append(f"{indent_str}| {index + 1} | {item.qty} | [{item.name}]({item.url}) | {item.type} |")
            else:
                rows.append(f"{indent_str}| {index + 1} | {item.qty} | {item.name} | {item.type} |")
        return "\n".join(rows)


def get_page_meta(page):
    try:
        return PageMeta(**page.meta)
    except ValidationError as error:
        print(str(error))
        raise

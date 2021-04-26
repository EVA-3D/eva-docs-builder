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


class PageMeta(BaseModel):
    satisfies: List[str]
    type: Optional[str] = ""
    uid: Optional[str]
    badges: Optional[List[str]]
    contributors: Optional[List[str]]
    repo_url: Optional[Optional[str]]
    cad_url: Optional[Optional[str]]
    satisfies: Optional[List[Satisfies]]
    hide: Optional[List[str]]


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


def get_page_meta(page):
    try:
        return PageMeta(**page.meta)
    except ValidationError as error:
        print(str(error))
        raise

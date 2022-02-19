from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Extra
from pydantic.networks import HttpUrl
from slugify import slugify


class OnshapeMeta(BaseModel):
    uid: str
    cad_url: HttpUrl

    @property
    def uid_slug(self):
        return slugify(self.uid)


class BasePageMeta(BaseModel):
    title: str
    icon: Optional[str]
    description: Optional[str]
    theme: Optional[str]
    tags: Optional[List[str]]
    hide: Optional[List[str]]
    onshape: Optional[OnshapeMeta]

    class Config:
        extra = Extra.allow


class EVAMainPageMeta(BasePageMeta):
    spec: Optional[str]
    type: Optional[str] = ""
    badges: Optional[List[str]]
    contributors: Optional[List[str]]
    usage: Optional[str]

    @property
    def percentage(self):
        return f"{(Decimal(self.usage) * 100).quantize(Decimal('.01'))} %"

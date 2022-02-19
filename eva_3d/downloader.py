import asyncio
import re
from tqdm import tqdm

from python_onshape_exporter.client import Onshape
from python_onshape_exporter.schemas import BOMTable
from slugify import slugify


CAD_URL_PATTERN = re.compile(
    r".*documents\/(?P<did>.+)\/w\/(?P<wid>.+)\/e\/(?P<eid>.+)"
)


class Downloader:
    def __init__(self, onshape_access_key, onshape_secret_key):
        self.onshape_access_key = onshape_access_key
        self.onshape_secret_key = onshape_secret_key

    @staticmethod
    def safe_filename(filename):
        return slugify(filename)

    def split_cad_url(self, cad_url):
        match = CAD_URL_PATTERN.match(cad_url)
        if not match:
            raise Exception(f"Bad CAD link {cad_url}")
        return (
            match.group("did"),
            match.group("wid"),
            match.group("eid"),
        )

    async def fetch_image(self, onshape, did, wid, eid):
        image_response = await onshape.get_shaded_view(
            did=did,
            wid=wid,
            eid=eid,
        )
        return image_response["images"][0]

    async def fetch_bom(self, onshape, assembly_name, did, wid, eid):
        onshape_data = await onshape.get_assembly_bom(
            did=did,
            wid=wid,
            eid=eid,
        )
        return BOMTable.parse_onshape(assembly_name, onshape_data)

    async def fetch_stl(
        self, onshape, name, did, wvm_id, wvm_type, eid, part_id, configuration, stl_bar
    ):
        stl = await onshape.export_part(
            did, wvm_id, wvm_type, eid, part_id, configuration
        )

        stl_bar.update(1)
        return name, stl

    async def download(self, n, assembly_name, cad_url, pages_bar):
        did, wid, eid = self.split_cad_url(cad_url)
        async with Onshape(
            access_key=self.onshape_access_key,
            secret_key=self.onshape_secret_key,
        ) as onshape:
            results = await asyncio.gather(
                self.fetch_image(onshape, did, wid, eid),
                self.fetch_bom(onshape, assembly_name, did, wid, eid),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, BaseException):
                    raise result

            printable_items = [
                bom_item for bom_item in results[1].items if bom_item.is_printable
            ]
            with tqdm(
                desc=f"Exporting SLTs from Onshape for {assembly_name}: ",
                total=len(printable_items),
                position=n + 1,
            ) as stl_bar:
                coros = [
                    self.fetch_stl(
                        onshape=onshape,
                        name=bom_item.name,
                        did=bom_item.source.did,
                        wvm_id=bom_item.source.wvm_id,
                        wvm_type=bom_item.source.wvm_type,
                        eid=bom_item.source.eid,
                        part_id=bom_item.source.part_id,
                        configuration=bom_item.source.configuration,
                        stl_bar=stl_bar,
                    )
                    for bom_item in printable_items
                ]
                stl_results = await asyncio.gather(*coros)
                for stl_result in stl_results:
                    if isinstance(stl_result, BaseException):
                        raise stl_result
            pages_bar.update(1)
        return results[0], results[1], stl_results

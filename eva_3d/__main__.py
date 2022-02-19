import asyncio
import logging
from pathlib import Path
import shutil
from base64 import b64decode
from zipfile import ZipFile, ZIP_DEFLATED

import click
from mkdocs import config
from mkdocs.commands import build
from python_onshape_exporter.client import Onshape
from sqlmodel import Session
from tqdm import tqdm

from eva_3d.downloader import Downloader
from eva_3d.db import create_db_and_tables, engine, BOMTable, BOMItem, remove_page_bom

DOWNLOAD_SEMAPHORE = asyncio.Semaphore(5)

logging.basicConfig(level=logging.ERROR, force=True)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)


@click.group()
def main():
    pass


@main.group()
@click.pass_context
def page(ctx):
    mkdocs_config = config.load_config(site_dir="/tmp/eva-3d-unpack")
    build.build(mkdocs_config)
    ctx.obj = {}
    ctx.obj["mkdocs_config"] = mkdocs_config


async def download_and_save(n, session, downloader, page, pages_bar):
    remove_page_bom(session, page.meta.onshape.uid)

    b64image, bom, stls = await downloader.download(
        n, page.meta.onshape.uid, page.meta.onshape.cad_url, pages_bar
    )

    image_path = (
        Path(page.file.abs_src_path)
        / ".."
        / "assets"
        / f"{Downloader.safe_filename(page.meta.onshape.uid)}.png"
    ).resolve()

    image_path.parent.mkdir(parents=True, exist_ok=True)
    with open(image_path, "wb") as image_file:
        image_file.write(b64decode(b64image))

    for name, stl in stls:
        stl_path = (
            Path(page.file.abs_src_path) / ".." / "stls" / f"{name}.stl"
        ).resolve()

        shutil.rmtree(stl_path, ignore_errors=True)
        stl_path.parent.mkdir(parents=True, exist_ok=True)

        with open(stl_path, "wb") as stl_file:
            stl_file.write(stl)

    bom_table = BOMTable(name=page.meta.onshape.uid)

    for item in bom.items:
        session.add(
            BOMItem(
                name=item.name,
                material=item.material,
                quantity=item.quantity,
                bom_table=bom_table,
            )
        )
    session.commit()


async def download_all(session, downloader, pages):
    pages_with_cad = [page for page in pages if page.meta.onshape]

    with tqdm(
        desc="Processing pages: ", total=len(pages_with_cad), position=0
    ) as pages_bar:
        coros = [
            download_and_save(n, session, downloader, page, pages_bar)
            for n, page in enumerate(pages_with_cad)
        ]
        async with DOWNLOAD_SEMAPHORE:
            return await asyncio.gather(*coros)


@page.command()
@click.pass_context
@click.option("--page-uid", default=None, type=str)
@click.option("--path", default=None, type=click.Path())
@click.option(
    "--onshape-access-key", envvar="ONSHAPE_ACCESS", prompt=True, hide_input=True
)
@click.option(
    "--onshape-secret-key", envvar="ONSHAPE_SECRET", prompt=True, hide_input=True
)
def download(
    ctx,
    path,
    onshape_access_key,
    onshape_secret_key,
    page_uid=None,
):
    create_db_and_tables()
    session = Session(engine)

    mkdocs_config = ctx.obj["mkdocs_config"]
    plugin = mkdocs_config["plugins"]["eva-3d-plugin"]
    downloader = Downloader(onshape_access_key, onshape_secret_key)

    pages = plugin.pages

    if page_uid:
        pages = [page for page in pages if page.meta.onshape.uid == page_uid]

    if path:
        pages = [
            page for page in pages if Path(path) in Path(page.file.src_path).parents
        ]

    results = asyncio.run(download_all(session, downloader, pages))
    result = results[0]


@main.command()
@click.pass_context
def gather_stls(ctx):
    all_stls = (Path(".") / "stls").absolute()
    shutil.rmtree(all_stls, ignore_errors=True)
    all_stls.mkdir(parents=True)

    stl_paths = Path("docs").rglob("*.stl")

    for src_stl_path in stl_paths:
        dst_stl_path = (all_stls / Path(*src_stl_path.parts[1:])).resolve()
        dst_stl_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_stl_path, dst_stl_path)

    with ZipFile(all_stls.parent / "stls.zip", "w", ZIP_DEFLATED) as zip_file:
        for file_path in all_stls.rglob("*.stl"):
            zip_file.write(file_path, file_path.relative_to(all_stls.parent))


if __name__ == "__main__":
    main(prog_name="python -m eva-3d")

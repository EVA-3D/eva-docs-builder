import sys
import csv
from pathlib import Path
import shutil
import zipfile

import click
from mkdocs import config
from mkdocs.commands import build


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


@page.command()
@click.pass_context
def unpack(ctx):
    mkdocs_config = ctx.obj["mkdocs_config"]
    unpacker =  mkdocs_config["plugins"]["eva-3d-plugin"].unpacker
    all_stls = (Path(".") / "stls").absolute()
    unpacker.unpack_all(all_stls)
    unpacker.archive(all_stls)


@page.command()
@click.pass_context
@click.argument("vendor_name", type=str)
@click.option("vendor_name", type=str)
def vendor_superbom(ctx, vendor_name):
    # TODO: move this to post build and walk to find all vendors/mappings
    # TODO: on post build generate a blank _template.csv to compare between releases
    mkdocs_config = ctx.obj["mkdocs_config"]
    superbom =  mkdocs_config["plugins"]["eva-3d-plugin"].superbom
    vendor_mapping_file_path = (Path(".") / "vendors" / f"{vendor_name}.csv")
    vendor_mapping = {}
    with open(vendor_mapping_file_path, newline="") as csvfile:
        for row in csv.DictReader(csvfile, delimiter=",", quotechar='"'):
            vendor_mapping[row["eva_part_name"]] = {
                "name": row["vendor_part_name"],
                "sku": row["vendor_sku"],
                "ignore": True if row["vendor_ignore"] else False,
            }
    
    print("qty,vendor_sku,vendor_part_name,eva_part_name")
    for part in superbom.parts:
        vendor_data = vendor_mapping[part.name]
        if vendor_data["ignore"]:
            continue
        print(f"{part.qty},{vendor_data['sku']},{vendor_data['name']},{part.name}")



if __name__ == "__main__":
    main(prog_name="python -m eva-3d")

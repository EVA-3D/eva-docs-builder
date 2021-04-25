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


@main.command()
def unpack():
    mkdocs_config = config.load_config(site_dir="/tmp/eva-3d-unpack")
    build.build(mkdocs_config)
    unpacker =  mkdocs_config["plugins"]["eva-3d-plugin"].unpacker
    all_stls = (Path(".") / "docs" / "stls").absolute()
    unpacker.unpack_all(all_stls)
    unpacker.archive(all_stls)


if __name__ == "__main__":
    main(prog_name="python -m eva-3d")

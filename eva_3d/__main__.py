import csv
from pathlib import Path
import shutil
import zipfile

import click


@click.group()
def main():
    pass


@main.command()
@click.argument("bom-file", type=click.File("r"))
@click.argument("zip-file", type=click.Path(exists=True))
@click.argument("stl-out-dir", type=click.Path())
def unpack_stls(bom_file, zip_file, stl_out_dir):
    files = set()
    reader = csv.DictReader(bom_file, delimiter=",", quotechar='"')
    for row in reader:
        if "Material" not in row:
            raise Exception("export a BOM with a material column")
        if "Name" not in row:
            raise Exception("export a BOM with a name column")
        if row["Material"].upper() == "PETG":
            files.add(f"{row['Name']}.stl")

    stl_out_dir = Path(stl_out_dir)
    # if Path(stl_out_dir).exists():
    #     shutil.rmtree(stl_out_dir)
    stl_out_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            for target_file in files:
                if target_file in file_name:
                    zip_ref.extract(file_name, stl_out_dir)

    for stl_file in stl_out_dir.iterdir():
        try:
            new_name = stl_file.name.split(" - ")[1]
        except IndexError:
            continue
        stl_file.rename(Path(stl_file.parent, new_name))

    print("works!")


if __name__ == "__main__":
    main(prog_name="python -m eva-3d")

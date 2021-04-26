import csv
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import shutil


class Unpacker:
    def __init__(self):
        self.zip_cache = set()
        self.pages = []

    def _is_zip(self, path) -> bool:
        return path.is_file() and path.suffix == ".zip"

    def _is_csv(self, path) -> bool:
        return path.is_file() and path.suffix == ".csv"

    def _find_zip_files(self, page):
        page_dir = (Path(page.file.abs_src_path) / "..").resolve()
        downloads_dir = page_dir / "downloads"
        try:
            for path in downloads_dir.iterdir():
                if path not in self.zip_cache and self._is_zip(path):
                    self.zip_cache.add(path)
                    yield path
        except (NotADirectoryError, FileNotFoundError) as exc:
            pass

    def add_page(self, page):
        if page not in self.pages:
            self.pages.append(page)

    def get_files_from_boms(self, path):
        bom_dir = (path.parent / ".." / "bom").resolve()
        stl_file_names = set()
        if not bom_dir.exists():
            raise Exception(
                "ERROR: trying to unpack zip for a module that has no BOM dir"
            )
        for csv_path in bom_dir.iterdir():
            if not self._is_csv(csv_path):
                continue
            with open(csv_path, newline="") as csvfile:
                for row in csv.DictReader(csvfile, delimiter=",", quotechar='"'):
                    if row["Material"].upper() == "PETG":
                        stl_file_names.add(f'{row["Name"]}.stl')
        return stl_file_names

    def unpack_all(self, all_stls):
        shutil.rmtree(all_stls, ignore_errors=True)
        all_stls.mkdir()
        for page in self.pages:
            page_dir = (Path(page.file.abs_src_path) / "..").resolve()
            stl_path = page_dir / "stls"

            zip_files = list(self._find_zip_files(page))
            missing_files = set()
            extracted_files = set()
            files_from_bom = set()

            if zip_files:
                shutil.rmtree(stl_path, ignore_errors=True)
                stl_path.mkdir()

            for zip_path in zip_files:
                print(f"Extracting {zip_path}")
                files_from_bom = self.get_files_from_boms(zip_path)
                with ZipFile(zip_path) as zip_file:
                    for file_name in zip_file.namelist():
                        try:
                            new_file_name = file_name.split(" - ")[1]
                        except IndexError as exc:
                            # probably redundant compositions from Onshape
                            # like the mosquito object
                            continue
                        if new_file_name in files_from_bom:
                            zip_file.extract(file_name, stl_path)
                            shutil.move(stl_path / file_name, stl_path / new_file_name)
                            extracted_files.add(new_file_name)

            if stl_path.exists():
                shutil.copytree(stl_path, all_stls, dirs_exist_ok=True)
            
            missing_files = files_from_bom.difference(extracted_files)
            if missing_files:
                raise Exception(
                    f"Not all files from BOM were found in the zip files: {missing_files}, on {page}"
                )

    def archive(self, all_stls):
        with ZipFile(all_stls.parent / "stls.zip", "w", ZIP_DEFLATED) as zip_file:
            for file_path in all_stls.iterdir():
                zip_file.write(file_path, file_path.name)

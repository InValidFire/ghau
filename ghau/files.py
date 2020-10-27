#  Copyright (c) 2020.  InValidFire
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
#  associated documentation files (the "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
#  following conditions:
#
#  The above copyright notice and this permission notice shall be included in all copies or substantial
#  portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#  INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#  PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
#  CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
#  OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import shutil
import zipfile
import logging
from ivf import files

import requests

log = logging.getLogger("ghau")


def download(url: str, save_file: str):
    """Download a file from the given url and save it to the given save_file.

    :param url: url of the file to download.
    :type url: str
    :param save_file: file to save the downloaded to.
    :type save_file: str"""
    r = requests.get(url, stream=True)
    with open(save_file, "wb") as fd:
        i = 0
        for chunk in r.iter_content(chunk_size=512):
            if chunk:
                i += 1
                fd.write(chunk)
                log.debug(f"Wrote chunk {i} to {save_file}")


def extract_zip(extract_path, file_path, wl: list):
    """Extracts files from the given zip file_path into the given extract_path and performs cleanup operations.

    Will not overwrite files present in the given whitelist.

    :param extract_path: path to extract the contents of the given zip to.
    :type extract_path: str
    :param file_path: path of the zip to extract.
    :type file_path: str
    :param wl: whitelist to avoid overwriting files from.
    :type wl: list"""
    program_dir = files.get_program_dir()

    log.debug(program_dir)
    log.debug(f"Extracting: {file_path}")
    with zipfile.ZipFile(file_path, "r") as zf:
        zf.extractall(extract_path)
        extract_folder = files.get_program_dir().joinpath("tmp")
        for item in zf.infolist():
            if item.is_dir():
                extract_folder = program_dir.joinpath(item.filename)
                break
    for path in extract_folder.glob("**/*"):
        log.debug(path)
        rpath = path.relative_to(extract_folder)
        log.debug(program_dir.joinpath(rpath))
        log.debug(f"WHITELIST: {wl}, PATH: {rpath}")
        if rpath in wl:
            log.debug(f"MATCH: {rpath}")
        if path.is_dir():
            if not program_dir.joinpath(rpath).exists():
                log.debug(f"Directory '{rpath}' not found, creating.")
                program_dir.joinpath(rpath).mkdir()
        elif path.is_file() and rpath not in wl:
            log.debug(f"Moving file '{path}' to '{program_dir.joinpath(rpath)}'")
            shutil.move(str(path), str(program_dir.joinpath(rpath)))
    shutil.rmtree(extract_folder)
    file_path.unlink()

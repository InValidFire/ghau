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

import os
import sys
import shutil
import zipfile
import logging
import pathlib

import requests
from wcmatch import wcmatch

log = logging.getLogger("ghau")


def message(msg, mode: str = "debug"):
    """Sends a message to the console if send is true. Used to easily control debug and error message output."""
    if mode == "debug":
        log.debug(msg)
    elif mode == "info":
        log.info(msg)
    elif mode == "warning":
        log.warning(msg)
    elif mode == "critical":
        log.critical(msg)
    elif mode == "exception":
        log.exception(msg)


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
                message("Wrote chunk {} to {}".format(str(i), save_file), "debug")


def extract_zip(extract_path, file_path, wl: list):
    """Extracts files from the given zip file_path into the given extract_path and performs cleanup operations.

    Will not overwrite files present in the given whitelist.

    :param extract_path: path to extract the contents of the given zip to.
    :type extract_path: str
    :param file_path: path of the zip to extract.
    :type file_path: str
    :param wl: whitelist to avoid overwriting files from.
    :type wl: list"""
    program_dir = pathlib.Path(os.path.realpath(os.path.dirname(sys.argv[0])))

    message(program_dir, "debug")
    message("Extracting: {}".format(file_path), "debug")
    with zipfile.ZipFile(file_path, "r") as zf:
        zf.extractall(extract_path)
        for item in zf.infolist():
            if item.is_dir():
                extract_folder = pathlib.Path(os.path.join(program_dir, item.filename))
                break
    for path in extract_folder.glob("**/*"):
        message(path, "debug")
        rpath = path.relative_to(extract_folder)
        message(program_dir.joinpath(rpath), "debug")
        if path.is_dir():
            if not program_dir.joinpath(rpath).exists():
                message("Directory '{}' not found, creating.".format(rpath), "debug")
                program_dir.joinpath(rpath).mkdir()
        elif path.is_file() and str(program_dir.joinpath(rpath)) not in wl:
            message("Moving file '{}' to '{}'".format(path, program_dir.joinpath(rpath)))
            shutil.move(str(path), str(program_dir.joinpath(rpath)))
    shutil.rmtree(extract_folder)
    os.remove(file_path)


def clean_files(file_list: list):
    """Delete all files in the file_list. Used to perform cleaning if ghau.update.Update.clean is enabled.

    :param file_list: list of files to delete.
    :type file_list: list"""
    for path in file_list:
        message("Removing path {}".format(path), "debug")
        os.remove(path)


def load_dict(name: str, root: str, dictobj: dict) -> list:
    """Filter directory based on given cleanlist. Returns paths of given files. This function utilizes
        wcmatch to identify files.

        :param name: what to call this event in the debug logs.
        :type name: str
        :param root: directory to start the file search in.
        :type root: str
        :param dictobj: unprocessed dictionary to load.
        :type dictobj: dict

        :returns list: paths of files found through the cleanlist."""
    file_search = ""
    exclusions = ""
    f, e = 0, 0
    for key in dictobj.keys():
        if dictobj[key] is False:
            if f == 0:  # wcmatch requires no '|' on the first entry.
                file_search += key
            else:
                file_search += "|" + key
            f += 1
        elif dictobj[key] is True:
            if e == 0:
                exclusions += key
            else:
                exclusions += "|" + key
            e += 1
    message("{} file_search: {}".format(name, file_search), "debug")
    message("{} exclusions: {}".format(name, exclusions), "debug")
    message("{} is searching for files in directory: {}".format(name, root), "debug")
    pl = wcmatch.WcMatch(root, file_search, exclusions, flags=wcmatch.RECURSIVE | wcmatch.GLOBSTAR |
                         wcmatch.PATHNAME).match()
    return pl

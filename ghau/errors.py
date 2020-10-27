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

import logging
import datetime

from github import Github
from pathlib import Path
import ghau.files as files

log = logging.getLogger('ghau')

class GhauError(Exception):
    """Base Exception class"""
    pass


class GitRepositoryFoundError(GhauError):
    """Raised when a git repository is detected."""
    def __init__(self):
        self.message = "Git Repository detected, aborting update process to protect file structure."


class GithubRateLimitError(GhauError):
    """Raised when exceeding GitHub's API rate."""
    def __init__(self, resettime):
        self.message = ("Current Github API rate limit reached. Cannot check for updates at this time.\n"
                        "Scheduled to reset on " +
                        datetime.datetime.fromtimestamp(resettime).strftime('%B %d at %H:%M:%S'))


class ReleaseNotFoundError(GhauError):
    """Raised when there are no releases found for the requested repository."""
    def __init__(self, repo: str):
        self.message = (f"No releases found for repository {repo}, aborting.")


class ReleaseAssetError(GhauError):
    """Raised when there is no asset found in the release by the requested name"""
    def __init__(self, release, asset_name):
        self.message = (f"No asset '{asset_name}' found for release {release}, aborting")


class RepositoryNotFoundError(GhauError):
    """Raised when Github request returns a 404"""
    def __init__(self, repo: str):
        self.message = (f"The repository {repo} could not be found, aborting.")


class NoAssetsFoundError(GhauError):
    """Raised when an asset request returns no asset list"""
    def __init__(self, release):
        self.message = (f"No assets found for release {release}")


class InvalidDownloadTypeError(GhauError):
    """Raised when the download parameter value is not expected."""
    def __init__(self, download):
        self.message = (f"'download' parameter value '{download}' is not expected.")


class FileNotExeError(GhauError):
    """Raised when the file given is not an executable."""
    def __init__(self, file: str):
        self.message = (f"The file '{file}' is not an .exe")


class FileNotScriptError(GhauError):
    """Raised when the file given is not a python script."""
    def __init__(self, file: str):
        self.message = (f"The file '{file}' is not a python script.")


class LoopPreventionError(GhauError):
    """Raised when rebooting after an update, to prevent potential loops if user doesn't bump version number."""
    def __init__(self):
        self.message = "Booting after update install, skipping update check."


class NotAFileOrDirectoryError(GhauError):
    """Raised when a path leads to neither a file nor a directory"""
    def __init__(self, path):
        self.message = (f"Path is not a file or a directory {path}")


def devtest(root):  # TODO Improve dev environment detection
    """Tests for an active dev environment.

    :exception ghau.errors.GitRepositoryFoundError: stops the update process if a .git folder is found within
     the program directory"""
    if Path(root).joinpath(".git").exists():
        raise GitRepositoryFoundError


def ratetest(ratemin: int, token=None):
    """Tests available Github API rate.

    :exception ghau.errors.GithubRateLimitError: stops the update process if the available rates are below
     the ratemin."""
    g = Github(token)
    rl = g.get_rate_limit()
    if rl.core.remaining <= ratemin:
        raise GithubRateLimitError(rl.core.reset.timestamp())
    else:
        log.info(f"API requests remaining: {rl.core.remaining}")


def argtest(args: list, arg: str):
    """Raises an error if the specified arg is found in the given args.

    Used to determine if booting after an update installation.

    :exception ghau.errors.LoopPreventionError: stops the update process if booting after an update installation."""
    if arg in args:
        raise LoopPreventionError

def filetest(folder: Path, file: Path):
    if folder.joinpath(file).exists():
        raise LoopPreventionError

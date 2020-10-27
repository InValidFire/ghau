#  Copyright (c) 2020.  Elizabeth Housden
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
#
#
import os
import sys
import shlex
import logging
from pathlib import Path

import ghau.errors as ge
import ghau.files as gf
from ivf import config, files
from github import Github, RateLimitExceededException, UnknownObjectException, GitRelease

log = logging.getLogger("ghau")

def _find_release_asset(release: GitRelease.GitRelease, asset: str) -> str:
    """Return the requested asset's download url from the given release.
    If no specific asset is requested, it will return the first one it comes across.

    :exception ghau.errors.ReleaseAssetError: No asset by given name was found.
    :exception ghau.errors.NoAssetsFoundError: No assets found for given release."""
    al = release.get_assets()
    if al.totalCount == 0:
        raise ge.NoAssetsFoundError(release.tag_name)
    if asset is None:
        return al[0].browser_download_url
    for item in al:
        if item.name == asset:
            log.debug(f"Found asset {item.name} with URL: {item.browser_download_url}")
            return item.browser_download_url
        raise ge.ReleaseAssetError(release.tag_name, asset)


def _do_update(local, online):
    """Compares the given versions, returns True if the values are different."""
    x = True if online != local else False
    return x


def _load_release(repo: str, pre_releases: bool, auth) -> GitRelease.GitRelease:
    """Returns the latest release (or pre_release if enabled) for the loaded repository.

    :exception ghau.errors.ReleaseNotFoundError: No releases found for given repository.

    :exception ghau.errors.GithubRateLimitError: Hit the rate limit in the process of loading the release.

    :exception ghau.errors.RepositoryNotFoundError: Given repository is not found."""
    g = Github(auth)
    try:
        if g.get_repo(repo).get_releases().totalCount == 0:  # no releases found
            log.debug("Release count is 0")
            raise ge.ReleaseNotFoundError(repo)
        if pre_releases:
            log.debug("Accepting pre-releases")
            return g.get_repo(repo).get_releases()[0]
        elif not pre_releases:
            log.debug("Accepting full releases")
            for release in g.get_repo(repo).get_releases():
                log.debug(f"Checking release {release.tag_name}")
                if not release.prerelease:
                    log.debug(f"Release found {release.tag_name}")
                    return release
            log.debug("Zero non-pre-release releases found")
            raise(ge.ReleaseNotFoundError(repo))
    except RateLimitExceededException:
        reset_time = g.rate_limiting_resettime
        raise ge.GithubRateLimitError(reset_time)
    except UnknownObjectException:
        raise ge.RepositoryNotFoundError(repo)


def _run_cmd(command: str):
    """Run the given command and close the python interpreter.
    If no command is given, it will just close. Does not currently support Windows OS."""
    if sys.platform == "win32" and command is not None:
        log.info("Windows Platform currently unsupported with reboots. However WSL works.")
    elif sys.platform == "linux" and command is not None:
        cmd_split = shlex.split(command)
        sys.stdout.flush()
        os.execv(cmd_split[0], cmd_split[1:])
    sys.exit()

def python(file: Path) -> str:  # used to reboot to the given python file in the working directory.
    """Builds the command required to run the given python file if it is in the current working directory.

    Useful for building the command to place in the reboot parameter of :class:`ghau.update.Update`.

    This is the recommended way to reboot into a python file, as it adds an argument ghau detects to stop update loops.
    This will also ensure the file given is a python script.

    See also: :func:`ghau.update.exe`, :func:`ghau.update.cmd`

    :exception ghau.errors.FileNotScriptError: raised if the given file is not a python script.
    """
    if type(file) is str:
        file = Path(file)
    program_dir = files.get_program_dir()
    if file.suffix == ".py":
        executable = Path(sys.executable)
        file_path = program_dir.joinpath(file)
        return f"{executable} {executable.stem} {file_path}"
    else:
        raise ge.FileNotScriptError(file)


def exe(file: str) -> str:  # added for consistency. Boots file in working directory.
    """Added for consistency with ghau.update.python.

    Useful for building the command to place in the reboot parameter of :class:`ghau.update.Update`.

    This is the recommended way to reboot into an executable file, as it adds an argument ghau detects to stop update
    loops. This will also ensure the file given is an .exe file.

    See also: :func:`ghau.update.python`, :func:`ghau.update.cmd`

    :exception ghau.errors.FileNotExeError: raised if the given file is not an executable."""
    if type(file) is str:
        file = Path(file)
    if file.suffix == ".exe":
        return f"{file}"
    else:
        raise ge.FileNotExeError(file)


def cmd(command: str) -> str:  # same as exe
    """Added for consistency with ghau.update.python.

    Useful for building the command to place in the reboot parameter of :class:`ghau.update.Update`.

    This is the recommended way to reboot using a command, as it adds an argument ghau detects to stop update loops.

    See also: :func:`ghau.update.python`, :func:`ghau.update.exe`
    """
    return f"{command}"

def _run_func(func, func_arg, user_args):
        if func is not None and user_args is not None:
            func(func_arg, *user_args)
        elif func is not None:
            func(func_arg)


class Update:
    """Main class used to trigger updates through ghau.

    :param version: local version to check against online versions.
    :type version: str
    :param repo: github repository to check for updates in.
        Must be publicly accessible unless you are using a Github Token.
    :type repo: str
    :param pre-releases: accept pre-releases as valid updates, defaults to False.
    :type pre-releases: bool, optional
    :param reboot: command intended to reboot the program after a successful update installs.
    :type reboot: str, optional
    :param download: the type of download you wish to use for updates.
        Either "zip" (source code) or "asset" (uploaded files), defaults to "zip".
    :type download: str, optional
    :param asset: name of asset to download when set to "asset" mode.
    :type asset: str, optional.
    :param auth: authentication token used for accessing the Github API, defaults to None.
    :type auth: str, optional
    :param ratemin: minimum amount of API requests left before updates will stop, defaults to 20.
        Maximum is 60/hr for unauthorized requests, and 5000 for authorized requests.
    :type ratemin: int, optional.
    """
    def __init__(self, version: str, repo: str, pre_releases: bool = False,
                 reboot: str = None, download: str = "zip", asset: str = None,
                 auth: str = None, ratemin: int = 20, boot_check: bool = True,
                 success_func = None, fail_func = None, pre_update_func = None, fail_args = None, success_args = None, post_update_func = None,
                 pre_update_args = None, post_update_args = None):
        self.auth = auth
        self.ratemin = ratemin
        self.version = version
        self.repo = repo
        self.pre_releases = pre_releases
        self.whitelist = []
        self.reboot = reboot
        self.download = download
        self.asset = asset
        self.program_dir = files.get_program_dir()
        self.boot_check = boot_check

        #  functions for update control
        self.pre_update_func = pre_update_func
        self.pre_update_args = pre_update_args
        self.success_func = success_func
        self.success_args = success_args
        self.fail_func = fail_func
        self.fail_args = fail_args
        self.post_update_func = post_update_func
        self.post_update_args = post_update_args
        if files.get_program_dir().joinpath('ghau_temp').exists():
            data = config.load(files.get_program_dir().joinpath('ghau_temp'))
            self.success_args = data['args']
            _run_func(self.success_func, self.version, self.success_args)
            files.get_program_dir().joinpath('ghau_temp').unlink()

    def update(self):
        """Check for updates and install if an update is found.

        All expected exceptions triggered during the run of this method are automatically handled.
        They are intentionally raised to stop the update process should it be needed, not the entire program.

        An error message will be printed to the console summarizing what occurred when this happens.

        :exception ghau.errors.InvalidDownloadTypeError: an unexpected value was given to the download parameter of
            :class:`ghau.update.Update`."""
        try:
            if self.boot_check:
                ge.filetest(files.get_program_dir(), "ghau_temp")
            ge.devtest(self.program_dir)
            ge.ratetest(self.ratemin, self.auth)
            latest_release = _load_release(self.repo, self.pre_releases, self.auth)
            do_update = _do_update(self.version, latest_release.tag_name)
            if do_update:
                _run_func(self.pre_update_func, (self.version, latest_release.tag_name), self.pre_update_args)
                if self.download == "zip":
                    log.debug("Downloading Zip")
                    gf.download(latest_release.zipball_url, self.program_dir.joinpath("update.zip"))
                    gf.extract_zip(self.program_dir, self.program_dir.joinpath("update.zip"), self.whitelist)
                elif self.download == "asset":
                    log.debug("Downloading Asset")
                    asset_link = _find_release_asset(latest_release, self.asset)
                    gf.download(asset_link, self.asset)
                else:
                    raise ge.InvalidDownloadTypeError(self.download)
                data = {'args': self.success_args} # creates temp argument file if success_args exists
                config.save(files.get_program_dir().joinpath('ghau_temp'), data)
                _run_func(self.post_update_func, (self.version, latest_release.tag_name), self.post_update_args)
                log.info(f"Updated from {self.version} to {latest_release.tag_name}")
                self.restart()
            else:
                log.info("No update required.")
                _run_func(self.fail_func, "No update required.", self.fail_args)
        except (ge.GithubRateLimitError, ge.GitRepositoryFoundError, ge.ReleaseNotFoundError, ge.ReleaseAssetError,
                ge.FileNotExeError, ge.FileNotScriptError, ge.NoAssetsFoundError, ge.InvalidDownloadTypeError,
                ge.LoopPreventionError, ge.NotAFileOrDirectoryError) as e:
            log.info(e.message)
            _run_func(self.fail_func, e.message, self.fail_args)
            return

    def update_check(self):
        """Returns True if an update is available to download."""
        ge.ratetest(self.ratemin, self.auth)
        latest_release = _load_release(self.repo, self.pre_releases, self.auth)
        return _do_update(self.version, latest_release.tag_name)

    def restart(self):
        """Restarts the program"""
        log.info("restarting!")
        _run_cmd(self.reboot)

    def wl_test(self):
        """Test the whitelist and output what's protected.

        Useful for testing your whitelist configuration."""
        log.debug(self.whitelist)
        log.debug(self.whitelist)
        if len(self.whitelist) == 0:
            log.info("Nothing is protected by your whitelist.")
        else:
            log.info("Whitelist will protect the following from being overwritten during installation: ")
            for path in self.whitelist:
                log.info(path)

    def wl_files(self, *args: str):
        """Add files to the whitelist. This protects any listed files from deletion during update installation.
        Each file should be a string referring to its name.

        :param args: list of files to protect.
        :type args: str"""
        for item in args:
            item = Path(item)
            if not item.exists():
                raise FileNotFoundError(item)
            elif item.is_dir():
                for file in item.glob("**/*"):
                    self.whitelist.append(file)
            elif item.is_file():
                self.whitelist.append(item)
            else:
                raise ge.NotAFileOrDirectoryError
            log.debug(f"Loaded file {item} into the whitelist.")

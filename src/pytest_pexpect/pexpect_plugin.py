import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Generator, IO, List, Optional, Tuple, Union
from types import CodeType

import pexpect
import pytest
import time

log = logging.getLogger(__name__)
debug_sleep: bool = False


def pytest_addoption(parser: pytest.Parser) -> None:
    log.debug("==> pytest_addoption")

    parser.addoption('--pexpect-dry-run', action='store_true',
                     dest='pexpect_dry_run',
                     help='Dry run pexpect commands')

    log.debug("<== pytest_addoption")


def pytest_configure(config: pytest.Config) -> None:
    log.debug("==> pytest_configure")

    Pexpect.dry_run = config.option.pexpect_dry_run
    print(f"Dry run {Pexpect.dry_run}")

    log.debug("<== pytest_configure")


@dataclass
class ShellParams:
    name: str = "shell"
    env: Optional[str] = None
    cd_to_dir: str = "."


class PexpectException(Exception):

    def __init__(self,
                 message: str = "This is a pytest-pexpect exception") -> None:
        self.message = message
        super().__init__(self.message)


class PexpectForbiddenPatternException(PexpectException):

    def __init__(self, pattern: str, expected: Optional[str] = None) -> None:
        self.message = f"Forbidden pattern detected: {pattern}"
        if expected is not None:
            self.message += f", expected {expected}"
        super().__init__(self.message)


class Pexpect(object):
    dry_run: bool = False

    @staticmethod
    def r__str__(obj: Any) -> str:
        """This returns a human-readable string that represents the state of
        the object. """
        import pexpect
        s = [repr(obj),
             'version: ' + pexpect.__version__ +
             ' (' + pexpect.__revision__ + ')',
             'command: ' + str(obj.command), 'args: ' + str(obj.args),
             'searcher: ' + str(obj.searcher),
             'buffer (last 2000 chars): ' + str(obj.buffer)[-2000:],
             'after: ' + str(obj.after), 'match: ' + str(obj.match),
             'match_index: ' + str(obj.match_index),
             'exitstatus: ' + str(obj.exitstatus),
             'flag_eof: ' + str(obj.flag_eof), 'pid: ' + str(obj.pid),
             'child_fd: ' + str(obj.child_fd), 'timeout: ' + str(obj.timeout),
             'delimiter: ' + str(obj.delimiter),
             'logfile: ' + str(obj.logfile),
             'logfile_read: ' + str(obj.logfile_read),
             'logfile_send: ' + str(obj.logfile_send),
             'maxread: ' + str(obj.maxread),
             'ignorecase: ' + str(obj.ignorecase),
             'searchwindowsize: ' + str(obj.searchwindowsize),
             'delaybeforesend: ' + str(obj.delaybeforesend),
             'delayafterclose: ' + str(obj.delayafterclose),
             'delayafterterminate: ' + str(obj.delayafterterminate)]
        # changed from 100 to 2000 (default value of maxread 2000)
        # s.append('before (last 2000 chars): ' + str(self.before)[-2000:])
        # s.append('closed: ' + str(self.closed))
        return '\n'.join(s)

    @staticmethod
    def __nodeid_to_path(node_id: str) -> str:
        log.debug("==> __node_id_to_path node_id=%s" % node_id)

        node_id = node_id.replace("(", "")
        node_id = node_id.replace(")", "")
        node_id = node_id.replace("::", "_")
        node_id = node_id.replace("/", "_")

        log.debug("<== __node_id_to_path node_id=%s" % node_id)
        return node_id

    @staticmethod
    def _sleep(t: Union[int, float], text: Optional[str] = None,
               dry_run: bool = False) -> None:
        logtext = ""
        if text is not None:
            logtext = "(" + text + ") "
        log.debug("    sleep %d sec %s...", t, logtext)
        if not dry_run:
            if debug_sleep:
                n = t // 5  # 1 dot every 5 sec.
                t2 = t % 5
                import sys
                for i in range(int(n)):
                    time.sleep(5)
                    sys.stdout.write(".")
                    sys.stdout.flush()
                time.sleep(t2)
                sys.stdout.write("\n")
                sys.stdout.flush()
            else:
                time.sleep(t)

    @staticmethod
    def pexpect_spawn(command: str, args: Optional[List[str]] = None,
                      timeout: int = 30, maxread: int = 2000,
                      search_window_size: Optional[int] = None,
                      logfile: Optional[IO] = None, cwd: Optional[str] = None,
                      env: Optional[dict] = None,
                      ignore_sighup: bool = True,
                      str_override: Optional[CodeType] = None,
                      dry_run: bool = False) -> Optional[pexpect.spawn]:
        if args is None:
            args = []
        log.debug("==> Pexpect.pexpect_spawn command=%s timeout=%s ",
                  command, timeout)

        enc = {"encoding": 'utf-8'}
        spawn = None
        if not dry_run:
            spawn = pexpect.spawn(command, args=args, timeout=timeout,
                                  maxread=maxread,
                                  searchwindowsize=search_window_size,
                                  logfile=logfile,
                                  cwd=cwd, env=env,
                                  ignore_sighup=ignore_sighup, **enc)
            if spawn is None:
                raise Exception("pexpect.spawn() failed")
            spawn.__str__.__func__.__code__ = Pexpect.r__str__.__code__ \
                if str_override is None else str_override

        log.debug("<== Pexpect.pexpect_spawn")
        return spawn

    def __init__(self, request: pytest.FixtureRequest,
                 name: Optional[str] = None,
                 shell: Optional[pexpect.spawn] = None) -> None:
        log.debug("==> Pexpect __init__ request=%s shell=%s name=%s" % (
            request, shell, name))

        self.shell: Optional[pexpect.spawn] = shell
        self.set_name(name)
        self.dry_run: bool = Pexpect.dry_run
        self.request: pytest.FixtureRequest = request

        log.debug(
            "<== self.request=%r self.shell=%s self.name=%s"
            " self.dry_run=%s",
            self.request, self.shell, self.name, self.dry_run)

    def set_name(self, name: Optional[str]) -> None:
        log.debug("==> set_name")

        self.name: Optional[str] = name

        log.debug("<== set_name")

    def pexpect_shell(self, shell_cmd: str = "/bin/bash --noprofile",
                      cd_to_dir: str = ".", env: Optional[str] = None,
                      timeout: int = 30) -> 'Pexpect':
        log.debug("==> shell_cmd=%s cd_to_dir=%s env=%s",
                  shell_cmd, cd_to_dir, env)

        if not self.dry_run:
            logf = self.open_log_file(self.name)
            self.shell = Pexpect.pexpect_spawn(shell_cmd, dry_run=self.dry_run,
                                               timeout=timeout)
            self.shell.logfile_send = logf
            self.shell.logfile_read = logf
            self.expect_prompt()
            self.shell.sendline("PS1='\\u@\\h:\\w\\$ '")
            self.expect_prompt()
            if cd_to_dir:
                self.shell.sendline(f"cd {cd_to_dir}")
                self.expect_prompt()
            if env is not None:
                self.shell.sendline(env)
                self.expect_prompt()

        log.debug("<==")
        return self

    def nodeid_path(self) -> str:
        log.debug("==> nodeid_path self.request.node.nodeid=%s",
                  self.request.node.nodeid)

        ret = Pexpect.__nodeid_to_path(self.request.node.nodeid)

        log.debug("<== ret=%s", ret)
        return ret

    def get_tst_dir(self) -> str:
        tst_dir = f"logs/{self.nodeid_path()}"
        return tst_dir

    def make_tst_dir(self) -> None:
        tst_dir = self.get_tst_dir()
        if not os.path.exists(tst_dir):
            os.makedirs(tst_dir)

    def open_log_file(self, name: Optional[str]) -> IO:
        self.make_tst_dir()
        logname = f"{self.get_tst_dir()}/{name}.log"
        log.debug("Using logname %s" % logname)
        logf = open(logname, 'w')
        return logf

    def write_file_to_tst_dir(self, name: str, text: str) -> None:
        if not self.dry_run:
            with open(f"{self.get_tst_dir()}/{name}", "w") as file:
                file.write(text)

    def make_shell(self, params: Optional[ShellParams] = None) -> 'Pexpect':
        if params is None:
            params = ShellParams()
        log.debug("==> params=%s", params)

        self.set_name(params.name)
        self.pexpect_shell(cd_to_dir=params.cd_to_dir, env=params.env)

        log.debug("<==")
        return self

    def expect(self, pattern: Union[str, List[str]], timeout: int = -1,
               searchwindowsize: int = -1, async_: bool = False,
               forbidden_patterns: Optional[List[str]] = None,
               **kw: Any) -> int:
        """
        A function for handling expected patterns with optional parameters
        for timeout, search window size, and asynchronous processing.

        :see: https://pexpect.readthedocs.io/en/stable/api/pexpect.html#pexpect.spawn.expect # noqa: E501
        :param pattern: The expected pattern.
        :param timeout: The timeout value.
        :param searchwindowsize: The search window size.
        :param async_: The asynchronous processing flag.
        :param forbidden_patterns: The forbidden patterns.
       """
        log.debug("==> expect %s", pattern)
        ret = 0

        if not self.dry_run:
            if forbidden_patterns is not None:
                assert isinstance(forbidden_patterns, list)
                len_pattern = 1 if not isinstance(pattern,
                                                  list) else len(pattern)
                lst_pattern = [pattern] if not isinstance(pattern,
                                                          list) else pattern
                lst_pattern.extend(forbidden_patterns)
                log.debug("lst_pattern=%s", lst_pattern)
                res = self.shell.expect(lst_pattern, timeout=timeout,
                                        searchwindowsize=searchwindowsize,
                                        async_=async_, **kw)
                log.debug("res=%s", res)
                if res >= len_pattern:
                    raise PexpectForbiddenPatternException(lst_pattern[res])
            else:
                ret = self.shell.expect(pattern, timeout=timeout,
                                        searchwindowsize=searchwindowsize,
                                        async_=async_, **kw)

        log.debug("<== expect %s", pattern)
        return ret

    def e(self, *args: Any, **kwargs: Any) -> int:
        """
        Alias for expect
        """
        return self.expect(*args, **kwargs)

    def expect_prompt(self, timeout: int = -1) -> None:
        if not self.dry_run:
            log.debug("timeout=%s", timeout)
            self.shell.expect(r"\$|#", timeout=timeout)

    def close(self, force: bool = True) -> None:
        if not self.dry_run and self.shell is not None:
            try:
                self.shell.close(force)
            except Exception:
                log.debug("    trying once more after 10 seconds...")
                self.do_sleep(10)
                try:
                    self.shell.close(force)
                except Exception:
                    log.warning("Failed to close shell, IGNORING!")

    def send(self, s: str = '') -> int:
        log.debug("==> send %s", s)
        ret = 0

        if not self.dry_run:
            ret = self.shell.send(s)

        log.debug("<== ret %s", ret)
        return ret

    def sendline(self, s: str = '',
                 expect: Optional[Union[str, List[str]]] = None,
                 timeout: int = -1, searchwindowsize: int = -1,
                 async_: bool = False,
                 forbidden_patterns: Optional[List[str]] = None,
                 **kw: Any) -> int:
        """
        Send a line to the shell.
        Optionally perform expect
        Does nothing if dry_run is true.
        :param s: a line string
        :see: self.expect
        :return: the returned value from pexpect sendline
        """
        log.debug("==> sendline %s", s)
        ret = 0

        if not self.dry_run:
            ret = self.shell.sendline(s)

        if expect is not None:
            ret = self.expect(expect, timeout=timeout,
                              searchwindowsize=searchwindowsize,
                              async_=async_,
                              forbidden_patterns=forbidden_patterns, **kw)

        log.debug("<== ret %s", ret)
        return ret

    def s(self, *args: Any, **kwargs: Any) -> int:
        """
        Alias for sendline
        """
        return self.sendline(*args, **kwargs)

    def sendcontrol(self, char: str) -> int:
        log.debug("==> sendcontrol %c", char)
        ret = 0

        if not self.dry_run:
            ret = self.shell.sendcontrol(char)

        log.debug("<== ret %s", ret)
        return ret

    def flush(self) -> None:
        log.debug("==> flush")

        if not self.dry_run:
            self.shell.flush()

        log.debug("<== flush")

    def do_sleep(self, t: Union[int, float],
                 text: Optional[str] = None) -> None:
        Pexpect._sleep(t, text, dry_run=self.dry_run)


@pytest.fixture
def pexpect_object(request: pytest.FixtureRequest, name: str = "pexpect") -> (
        Generator)[Pexpect, None, None]:
    """
    A fixture that returns a Pexpect object.
    Closes the Pexpect object after the test.
    :param request: pytest request object
    :param name: The name of the Pexpect object.
    :yield: A Pexpect object.
    """
    log.debug("==> pexpect_object")

    ret = Pexpect(request, name=name)
    yield ret
    log.debug("pexpect_object after yield")
    ret.close()

    log.debug("<== pexpect_object")


@pytest.fixture
def pexpect_shell(pexpect_object: Pexpect, shell: ShellParams) -> (
        Generator)[Pexpect, None, None]:
    """
    A fixture that creates a pexpect shell using the provided shell parameters.
    Closes the Pexpect object after the test.
    :param pexpect_object: The pexpect object fixture.
    :param shell: The shell parameters to use.
    :return: A Pexpect object.
    """
    assert isinstance(shell, ShellParams)
    log.debug("==> pexpect_shell")

    pexpect_object.make_shell(shell)
    yield pexpect_object

    log.debug("<== pexpect_shell")


@pytest.fixture
def pexpect_factory(request: pytest.FixtureRequest) -> (
        Generator)[Callable[..., Union[Pexpect, Tuple[Pexpect, ...]]], None, None]:
    """
    A unified factory fixture that creates Pexpect objects with optional shell initialization.

    This fixture provides a flexible way to create one or more Pexpect objects for testing,
    with optional automatic shell initialization. It handles proper cleanup of all created
    objects automatically when the test completes.

    :param request: pytest request object (automatically injected)
    :yield: Factory function that creates Pexpect objects

    Usage Examples:
    ---------------

    # Create a single basic Pexpect object (no shell)
    def test_basic(pexpect_factory):
        pexpect_obj = pexpect_factory()
        # Use pexpect_obj...

    # Create multiple basic Pexpect objects
    def test_multiple_basic(pexpect_factory):
        obj1, obj2, obj3 = pexpect_factory(n=3)
        # Use obj1, obj2, obj3...

    # Create a single shell-initialized object
    def test_single_shell(pexpect_factory):
        shell_obj = pexpect_factory(shell_params=ShellParams(name="test_shell"))
        # shell_obj is ready to use with an active shell

    # Create multiple objects with same shell configuration
    def test_multiple_same_shell(pexpect_factory):
        shell1, shell2 = pexpect_factory(n=2, shell_params=ShellParams(cd_to_dir="/tmp"))
        # Both shells start in /tmp directory

    # Create multiple objects with different shell configurations
    def test_multiple_different_shells(pexpect_factory):
        params = [
            ShellParams(name="shell1", cd_to_dir="/home"),
            ShellParams(name="shell2", cd_to_dir="/tmp", env="export DEBUG=1")
        ]
        shell1, shell2 = pexpect_factory(shell_params=params)
        # shell1 starts in /home, shell2 starts in /tmp with DEBUG env var
    """
    log.debug("==> pexpect_factory")
    created_pexpects: List[Pexpect] = []

    def _create_pexpects(n: int = 1, shell_params: Optional[Union[ShellParams, List[ShellParams]]] = None) -> (
            Union)[Pexpect, Tuple[Pexpect, ...]]:
        """
        Factory function to create Pexpect objects with optional shell initialization.

        :param n: Number of Pexpect objects to create (ignored if shell_params is a list)
        :param shell_params: Shell configuration options:
            - None: Create n basic Pexpect objects without shell initialization
            - ShellParams: Create n Pexpect objects, all with the same shell configuration
            - List[ShellParams]: Create len(shell_params) objects, each with its own configuration
                                (the 'n' parameter is ignored in this case)

        :return: Single Pexpect object if creating one, otherwise tuple of Pexpect objects

        :raises ValueError: If n < 1 or if shell_params list is empty
        """
        if n < 1:
            raise ValueError("Number of objects to create must be at least 1")

        log.debug("==> _create_pexpects: n=%i, shell_params=%s", n,
                  shell_params)

        # Determine how many objects to create and their configurations
        configs: List[Optional[ShellParams]]
        if isinstance(shell_params, list):
            if not shell_params:
                raise ValueError("shell_params list cannot be empty")
            # List of shell params - create one object per param
            configs = shell_params
            count = len(shell_params)
            log.debug(
                "Creating %d objects with individual shell configurations",
                count)
        elif shell_params is not None:
            # Single shell param - create n objects with same config
            configs = [shell_params] * n
            count = n
            log.debug("Creating %d objects with same shell configuration",
                      count)
        else:
            # No shell params - create n basic objects
            configs = [None] * n
            count = n
            log.debug("Creating %d basic objects without shell initialization",
                      count)

        # Create the Pexpect objects
        ret: List[Pexpect] = []
        for i in range(count):
            log.debug("Creating Pexpect object %d/%d", i + 1, count)
            pexpect_obj = Pexpect(request)

            # Initialize shell if config provided
            if configs[i] is not None:
                log.debug("Initializing shell for object %d with params: %s",
                          i + 1, configs[i])
                pexpect_obj.make_shell(configs[i])

            ret.append(pexpect_obj)

        # Track for cleanup
        created_pexpects.extend(ret)
        log.debug("Tracking %d objects for cleanup", len(ret))

        # Return single object or tuple based on count
        result: Union[Pexpect, Tuple[Pexpect, ...]] = ret[
            0] if count == 1 else tuple(ret)

        log.debug("<== _create_pexpects: created %s", type(result).__name__)
        return result

    yield _create_pexpects

    log.debug("pexpect_factory teardown: cleaning up %d objects",
              len(created_pexpects))

    # Cleanup all created objects
    for i, pe in enumerate(created_pexpects):
        log.debug("Closing Pexpect object %d/%d: %r", i + 1,
                  len(created_pexpects), pe)
        try:
            pe.close()
        except Exception as e:
            log.warning("Failed to close Pexpect object %d: %s", i + 1, e)

    log.debug("<== pexpect_factory: cleanup complete")

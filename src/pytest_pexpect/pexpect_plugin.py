import logging
import os
from dataclasses import dataclass
from typing import List, Tuple, Union

import pexpect
import pytest
import time

log = logging.getLogger(__name__)
debug_sleep = False


def pytest_addoption(parser):
    log.debug("==> pytest_addoption")
    parser.addoption('--pexpect-dry-run', action='store_true',
                     dest='pexpect_dry_run',
                     help='Dry run pexpect commands')
    log.debug("<== pytest_addoption")


def pytest_configure(config):
    log.debug("==> pytest_configure")
    Pexpect.dry_run = config.option.pexpect_dry_run
    print(f"Dry run {Pexpect.dry_run}")
    log.debug("<== pytest_configure")


@dataclass
class ShellParams:
    name: str = "shell"
    env: str = None
    cd_to_dir: str = "."


class Pexpect(object):
    dry_run = False

    @staticmethod
    def r__str__(obj):
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
    def __nodeid_to_path(node_id):
        log.debug("==> __node_id_to_path node_id=%s" % node_id)
        node_id = node_id.replace("(", "")
        node_id = node_id.replace(")", "")
        node_id = node_id.replace("::", "_")
        node_id = node_id.replace("/", "_")
        log.debug("<== __node_id_to_path node_id=%s" % node_id)
        return node_id

    @staticmethod
    def _sleep(t, text=None, dry_run=False):
        logtext = ""
        if text is not None:
            logtext = "(" + text + ") "
        log.debug("    sleep %d sec %s...", t, logtext)
        if not dry_run:
            if debug_sleep:
                n = t / 5  # 1 dot every 5 sec.
                t2 = t % 5
                import sys
                for i in range(n):
                    time.sleep(5)
                    sys.stdout.write(".")
                    sys.stdout.flush()
                time.sleep(t2)
                sys.stdout.write("\n")
                sys.stdout.flush()
            else:
                time.sleep(t)

    @staticmethod
    def pexpect_spawn(command, args=None, timeout=30, maxread=2000,
                      search_window_size=None, logfile=None, cwd=None,
                      env=None,
                      ignore_sighup=True, str_override=None,
                      dry_run=False):
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

    def __init__(self, request, name=None, shell=None):
        log.debug("==> Pexpect __init__ request=%s shell=%s name=%s" % (
            request, shell, name))
        self.shell = shell
        self.set_name(name)
        self._debug = False
        self.dry_run = Pexpect.dry_run
        self.request = request
        log.debug(
            "<== self.request=%r self.shell=%s self.name=%s"
            " self.debug=%s self.dry_run=%s",
            self.request, self.shell, self.name, self._debug, self.dry_run)

    def set_name(self, name):
        log.debug("==> set_name")
        self.name = name
        log.debug("<== set_name")

    def pexpect_shell(self, shell_cmd="/bin/bash --noprofile",
                      cd_to_dir=".", env=None, timeout=30):
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

    def nodeid_path(self):
        log.debug("==> nodeid_path self.request.node.nodeid=%s",
                  self.request.node.nodeid)
        ret = Pexpect.__nodeid_to_path(self.request.node.nodeid)
        log.debug("<== ret=%s", ret)
        return ret

    def get_tst_dir(self):
        tst_dir = f"logs/{self.nodeid_path()}"
        return tst_dir

    def make_tst_dir(self):
        tst_dir = self.get_tst_dir()
        if not os.path.exists(tst_dir):
            os.makedirs(tst_dir)

    def open_log_file(self, name):
        self.make_tst_dir()
        logname = f"{self.get_tst_dir()}/{name}.log"
        log.debug("Using logname %s" % logname)
        logf = open(logname, 'w')
        return logf

    def write_file_to_tst_dir(self, name, text):
        if not self.dry_run:
            file = open(f"{self.get_tst_dir()}/{name}", "w")
            file.write(text)
            file.close()

    def make_shell(self, params=ShellParams()):
        log.debug("==> params=%s", params)
        self.set_name(params.name)
        self.pexpect_shell(cd_to_dir=params.cd_to_dir, env=params.env)
        log.debug("<==")
        return self

    def expect(self, pattern: str, timeout=-1, searchwindowsize=-1,
               async_=False, fail_on: List = None, **kw):
        """
        A function for handling expected patterns with optional parameters
        for timeout, search window size, and asynchronous processing.

        :see: https://pexpect.readthedocs.io/en/stable/api/pexpect.html#pexpect.spawn.expect # noqa: E501
        :param pattern: The expected pattern.
        :param timeout: The timeout value.
        :param searchwindowsize: The search window size.
        :param async_: The asynchronous processing flag.
        :param fail_on: The forbidden patterns.
       """
        log.debug("==> expect %s", pattern)
        if self._debug:
            log.debug("    %s.expect: \"%s\"", self.method_name(), pattern)
        ret = 0
        if not self.dry_run:
            if fail_on is not None:
                assert isinstance(fail_on, list)
                pattern = [pattern] if not isinstance(pattern,
                                                      list) else pattern
                lst_pattern = [pattern] + fail_on
                res = self.shell.expect(lst_pattern, timeout=timeout,
                                        searchwindowsize=searchwindowsize,
                                        async_=async_, **kw)
                if res >= len(pattern):
                    pytest.fail("Received forbidden value %s, expected %s",
                                lst_pattern[res], lst_pattern[0])
            else:
                ret = self.shell.expect(pattern, timeout=timeout,
                                        searchwindowsize=searchwindowsize,
                                        async_=async_, **kw)
        log.debug("<== expect %s", pattern)
        return ret

    def e(self, *args, **kwargs):
        """
        Alias for expect
        """
        return self.expect(*args, **kwargs)

    def expect_prompt(self, timeout=-1):
        if not self.dry_run:
            log.debug("timeout=%s", timeout)
            self.shell.expect(r"\$|#", timeout=timeout)

    def close(self, force=True):
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

    def send(self, s=''):
        log.debug("==> send %s", s)
        ret = 0
        if self._debug:
            log.debug("    send: \"%s\"", self.method_name())
        if not self.dry_run:
            ret = self.shell.send(s)
        log.debug("<== ret %s", ret)
        return ret

    def sendline(self, s=''):
        """
        Send a line to the shell.
        Does nothing if dry_run is true.
        :param s: a line string
        :return: the returned value from pexpect sendline
        """
        log.debug("==> sendline %s", s)
        ret = 0
        if self._debug:
            log.debug("    sendline: \"%s\"", self.method_name())
        if not self.dry_run:
            ret = self.shell.sendline(s)
        log.debug("<== ret %s", ret)
        return ret

    def s(self, *args, **kwargs):
        """
        Alias for sendline
        """
        return self.sendline(*args, **kwargs)

    def sendcontrol(self, char):
        log.debug("==> sendcontrol %c", char)
        ret = 0
        if not self.dry_run:
            ret = self.shell.sendcontrol(char)
        log.debug("<== ret %s", ret)
        return ret

    def flush(self):
        log.debug("==> flush")
        if not self.dry_run:
            self.shell.flush()
        log.debug("<== flush")

    def do_sleep(self, t, text=None):
        Pexpect._sleep(t, text, dry_run=self.dry_run)


@pytest.fixture
def pexpect_object(request, name: str = "pexpect") -> Pexpect:
    """
    A fixture that returns a Pexpect object.
    Closes the Pexpect object after the test.
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
def pexpect_shell(pexpect_object, shell) -> Pexpect:
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
def make_pexpects(request):
    """
    A fixture that creates factory functions that create Pexpect objects.
    Closes the Pexpect objects after the test.
    :param request:
    :yield: yields a factory function that creates Pexpect objects.
    """
    log.debug("==> make_pexpects")
    created_pexpects: List[Pexpect] = []

    def _make_pexpects(n: int = 1) -> Union[Pexpect, Tuple[Pexpect, ...]]:
        """
        A fixture function that creates Pexpect objects.
        It takes an optional parameter 'n' to specify the number of
        Pexpect objects to create.
        It returns a single Pexpect object if 'n' is 1,
        otherwise it returns a tuple of Pexpect objects.

        :param request: The pytest request object.
        :param n: The number of Pexpect objects to create.
        :return: A Pexpect object or a tuple of Pexpect objects.
        """
        log.debug("==> n=%i", n)

        ret = tuple(Pexpect(request) for _ in range(n))
        created_pexpects.extend(ret)
        ret = ret[0] if len(ret) == 1 else ret

        log.debug("<== ret=%r", ret)
        return ret

    yield _make_pexpects
    log.debug("make_pexpect after yield created_pexpects=%r",
              created_pexpects)

    for pe in created_pexpects:
        log.debug("closing=%r", pe)
        pe.close()

    log.debug("<== make_pexpects")


@pytest.fixture
def make_pexpect_shells(request, make_pexpects):
    """
    A fixture that creates factory functions that create Pexpect objects
    initialized with shell parameters.
    Closes the Pexpect objects after the test.
    :param request:
    :param make_pexpects: The fixture that creates Pexpect objects
    :yield: yields a factory function that creates Pexpect objects
    """
    log.debug("==> make_pexpect_shells")

    def _make_pexpect_shells(params: List[ShellParams] = [ShellParams()]) -> \
            Union[Pexpect, Tuple[Pexpect, ...]]:
        """
        A fixture function that creates Pexpect objects
        initialized with shell parameters.
        It takes an optional parameter 'params' representing the List of
        ShellParams to use for each Pexpect object
        (defaults to [ShellParams()]).
        It returns a single Pexpect object if params contains a single
        ShellParams, otherwise it returns a tuple of Pexpect objects.
        :param request: The pytest request object.
        :param params: The List of ShellParams to use for each Pexpect object.
        :return: A Pexpect object, or a tuple of Pexpect objects.
        """
        log.debug("==> params=%s", params)

        ret = [make_pexpects() for _ in range(len(params))]
        for s, param in zip(ret, params):
            s.make_shell(param)
        ret = ret[0] if len(ret) == 1 else tuple(ret)

        log.debug("<== ret=%r", ret)
        return ret

    yield _make_pexpect_shells
    log.debug("<== make_pexpect_shells")

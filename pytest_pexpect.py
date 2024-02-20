import logging
import os
from typing import List

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
             'delimiter: ' + str(obj.delimiter), 'logfile: ' + str(obj.logfile),
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
                      search_window_size=None, logfile=None, cwd=None, env=None,
                      ignore_sighup=True, str_override=None,
                      sh_name=None, dry_run=False):
        if args is None:
            args = []
        log.debug("pexpect_spawn() sh_name=%s", sh_name)
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
                raise Exception("pexpect.spawn() failed sh_name=%s", sh_name)
            spawn.__str__.__func__.__code__ = Pexpect.r__str__.__code__ \
                if str_override is None else str_override
        return spawn

    def __init__(self, request, shell=None, sh_name=None):
        log.debug("==> Pexpect __init__ request=%s shell=%s sh_name=%s" % (
            request, shell, sh_name))
        self.shell = shell
        self.sh_name = sh_name
        self._debug = False
        self.dry_run = Pexpect.dry_run
        self.request = request
        log.debug(
            "<== self.request=%r self.shell=%s self.sh_name=%s self.debug=%s self.dry_run=%s",
            self.request, self.shell, self.sh_name, self._debug, self.dry_run)

    def pexpect_shell(self, name, cd_to_dir=".", env=None,
                      dry_run=False):
        log.debug("name=%s cd_to_dir=%s env=%s", name, cd_to_dir, env)
        if not dry_run:
            logf = self.open_log_file(name)
            self.shell = Pexpect.pexpect_spawn('/bin/bash --noprofile',
                                               sh_name=name, dry_run=dry_run)
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

    def make_shell(self, name, cd_to_dir=".", env=None):
        log.debug(
            "==> Pexpect make_shell name=%s cd_to_dir=%s env=%s"
            % (name, cd_to_dir, env))
        self.pexpect_shell(name, cd_to_dir=cd_to_dir, env=env,
                           dry_run=self.dry_run)
        log.debug("<== Pexpect make_shell")
        return self

    def __getattr__(self, attr):
        log.debug("==> __getattr__ %s" % attr)
        shell = self.shell
        if attr == "s":
            attr = "sendline"
            shell = self
        if attr == "e":
            attr = "expect"
            shell = self
        log.debug("<== attr %s" % attr)
        return getattr(shell, attr) if shell is not None else "shell is None!"

    def expect(self, pattern, timeout=-1, searchwindowsize=-1, async_=False,
               fail_on=None, **kw):
        log.debug("==> expect %s", pattern)
        if self._debug:
            log.debug("    %s.expect: \"%s\"", self.sh_name, pattern)
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
            log.debug("    send: \"%s\"", self.sh_name)
        if not self.dry_run:
            ret = self.shell.send(s)
        log.debug("<== ret %s", ret)
        return ret

    def sendline(self, s=''):
        log.debug("==> sendline %s", s)
        ret = 0
        if self._debug:
            log.debug("    sendline: \"%s\"", self.sh_name)
        if not self.dry_run:
            ret = self.shell.sendline(s)
        log.debug("<== ret %s", ret)
        return ret

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
def make_pexpect(request):
    created_pexpects:List[Pexpect] = []

    def _make_pexpect(n: int = 1):
        log.debug("==> n=%i", n)
        if n < 2:
            ret = Pexpect(request)
            created_pexpects.append(ret)
        else:
            ret = [Pexpect(request) for _ in range(n)]
            created_pexpects.extend(ret)
            ret = tuple(ret)
        log.debug("<== ret=%r", ret)
        return ret

    yield _make_pexpect

    for pe in created_pexpects:
        log.debug("closing=%r", pe)
        pe.close()

import logging
import os

import pexpect
import pytest
import time

log = logging.getLogger(__name__)
debug_sleep = False


def pytest_addoption(parser):
    log.debug("==> pytest_addoption")
    parser.addoption('--pexpect-dry-run',  action='store_true',
                     dest='pexpect_dry_run',
                     help='Dry run pexpect commands')
    log.debug("<== pytest_addoption")


def pytest_configure(config):
    log.debug("==> pytest_configure")
    Pexpect.dry_run = config.option.pexpect_dry_run
    print(f"Dry run {Pexpect.dry_run}")
    log.debug("<== pytest_configure")


def r__str__(obj):
    """This returns a human-readable string that represents the state of
    the object. """
    import pexpect
    s = [repr(obj),
         'version: ' + pexpect.__version__ + ' (' + pexpect.__revision__ + ')',
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
         'maxread: ' + str(obj.maxread), 'ignorecase: ' + str(obj.ignorecase),
         'searchwindowsize: ' + str(obj.searchwindowsize),
         'delaybeforesend: ' + str(obj.delaybeforesend),
         'delayafterclose: ' + str(obj.delayafterclose),
         'delayafterterminate: ' + str(obj.delayafterterminate)]
    # changed from 100 to 2000 (default value of maxread 2000)
    # s.append('before (last 2000 chars): ' + str(self.before)[-2000:]) #same as buffer
    # s.append('closed: ' + str(self.closed))
    return '\n'.join(s)


class Pexpect(object):
    dry_run = False

    @staticmethod
    def nodeid_to_path(node_id):
        log.debug("==> node_id_to_path node_id=%s" % node_id)
        node_id = node_id.replace("(", "")
        node_id = node_id.replace(")", "")
        node_id = node_id.replace("::", "_")
        node_id = node_id.replace("/", "_")
        log.debug("<== node_id_to_path node_id=%s" % node_id)
        return node_id

    @staticmethod
    def make_tst_dir(path):
        tst_dir = Pexpect.get_tst_dir(path)
        if not os.path.exists(tst_dir):
            os.makedirs(tst_dir)

    @staticmethod
    def write_file_to_tst_dir(name, path, text):
        file = open(f"{Pexpect.get_tst_dir(path)}/{name}", "w")
        file.write(text)
        file.close()

    @staticmethod
    def get_tst_dir(path):
        tst_dir = f"logs/{path}" if path else "logs"
        return tst_dir
    @staticmethod
    def open_log_file(name, path=None):
        Pexpect.make_tst_dir(path)
        logname = f"{Pexpect.get_tst_dir(path)}/{name}.log"
        log.debug("Using logname %s" % logname)
        logf = open(logname, 'w')
        return logf

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
                      ignore_sighup=True, str_override=r__str__.__code__,
                      sh_name=None):  # TODO echo=True
        if args is None:
            args = []
        log.debug("pexpect_spawn() sh_name=%s", sh_name)
        enc = {"encoding": 'utf-8'}
        spawn = pexpect.spawn(command, args=args, timeout=timeout, maxread=maxread,
                              searchwindowsize=search_window_size, logfile=logfile,
                              cwd=cwd, env=env,
                              ignore_sighup=ignore_sighup, **enc)
        if spawn is None:
            raise Exception("pexpect.spawn() failed sh_name=%s", sh_name)
        if str_override is not None:
            # change __str__ in class spawn (for all instances TODO - only once??)
            spawn.__str__.__func__.__code__ = str_override

        return spawn
    def __init__(self, shell = None, sh_name=None):
        log.debug("==> Pexpect __init__ shell=%r sh_name=%s" % (shell, sh_name))
        self.shell = shell
        self.sh_name = sh_name
        self._debug = False
        self.dry_run = Pexpect.dry_run
        log.debug(
            "<== self.shell=%s self.sh_name=%s self.debug=%s self.dry_run=%s",
            self.shell, self.sh_name, self._debug, self.dry_run)

    @staticmethod
    def expect_prompt_in_shell(shell, timeout=-1):
        log.debug("timeout=%s", timeout)
        shell.expect(r"\$|#", timeout=timeout)
    @staticmethod
    def pexpect_shell(name, logfile_path=None, cd_to_dir=".", env=None):
        log.debug(f"name={name} logfile_path={logfile_path} cd_to_dir={cd_to_dir} env={env}")
        logf = Pexpect.open_log_file(name, logfile_path)
        shell = Pexpect.pexpect_spawn('/bin/bash --noprofile', sh_name=name)
        shell.logfile_send = logf
        shell.logfile_read = logf
        Pexpect.expect_prompt_in_shell(shell)
        shell.sendline("PS1='\\u@\\h:\\w\\$ '")
        Pexpect.expect_prompt_in_shell(shell)
        if cd_to_dir:
            shell.sendline(f"cd {cd_to_dir}")
            Pexpect.expect_prompt_in_shell(shell)
        if env is not None:
            shell.sendline(env)
            Pexpect.expect_prompt_in_shell(shell)
        return shell
    def make_shell(self, name, logfile_path=None, cd_to_dir=".", env=None):
        log.debug("==> Pexpect make_shell name=%s logfile_path=%s cd_to_dir=%s env=%s"
                  % (name, logfile_path, cd_to_dir, env))
        if not self.dry_run:
            self.shell = Pexpect.pexpect_shell(name, logfile_path, cd_to_dir=cd_to_dir, env=env)
        log.debug("<== Pexpect make_shell")

    def __getattr__(self, attr):
        log.debug("==> __getattr__ %s" % (attr))
        shell = self.shell
        if attr == "s":
            attr = "sendline"
            shell = self
        if attr == "e":
            attr = "expect"
            shell = self
        log.debug("<== attr %s" % (attr))
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
                pattern = [pattern] if not isinstance(pattern, list) else pattern
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
            Pexpect.expect_prompt_in_shell(self.shell, timeout=timeout)

    def close(self, force=True):
        if not self.dry_run and self.shell is not None:
            try:
                self.shell.close(force)
            except:
                log.debug("    trying once more after 10 seconds...")
                self.app._sleep(10)
                try:
                    self.shell.close(force)
                except:
                    log.warning("Failed to close shell, IGNORING!")

    def send(self, s=''):
        log.debug("==> send %s", s)
        ret = 0
        if self._debug:
            log.debug("    send: \"%s\"", self.sh_name )
        if not self.dry_run:
            ret =  self.shell.send(s)
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
        Pexpect._sleep(t,text, dry_run=self.dry_run)

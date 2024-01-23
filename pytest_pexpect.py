import logging
import os
import time

import pexpect
import pytest

log = logging.getLogger(__name__)
debug_sleep = False


def __str__(self):
    """This returns a human-readable string that represents the state of
    the object. """
    import pexpect
    s = [repr(self),
         'version: ' + pexpect.__version__ + ' (' + pexpect.__revision__ + ')',
         'command: ' + str(self.command), 'args: ' + str(self.args),
         'searcher: ' + str(self.searcher),
         'buffer (last 2000 chars): ' + str(self.buffer)[-2000:],
         'after: ' + str(self.after), 'match: ' + str(self.match),
         'match_index: ' + str(self.match_index),
         'exitstatus: ' + str(self.exitstatus),
         'flag_eof: ' + str(self.flag_eof), 'pid: ' + str(self.pid),
         'child_fd: ' + str(self.child_fd), 'timeout: ' + str(self.timeout),
         'delimiter: ' + str(self.delimiter), 'logfile: ' + str(self.logfile),
         'logfile_read: ' + str(self.logfile_read),
         'logfile_send: ' + str(self.logfile_send),
         'maxread: ' + str(self.maxread), 'ignorecase: ' + str(self.ignorecase),
         'searchwindowsize: ' + str(self.searchwindowsize),
         'delaybeforesend: ' + str(self.delaybeforesend),
         'delayafterclose: ' + str(self.delayafterclose),
         'delayafterterminate: ' + str(self.delayafterterminate)]
    # changed from 100 to 2000 (default value of maxread 2000)
    # s.append('before (last 2000 chars): ' + str(self.before)[-2000:]) #same as buffer
    # s.append('closed: ' + str(self.closed))
    return '\n'.join(s)


def pexpect_spawn(command, args=None, timeout=30, maxread=2000,
                  search_window_size=None, logfile=None, cwd=None, env=None,
                  ignore_sighup=True, str_override=__str__.__code__,
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


def nodeid_to_path(node_id):
    log.debug("==> node_id_to_path node_id=%s" % node_id)
    node_id = node_id.replace("(", "")
    node_id = node_id.replace(")", "")
    node_id = node_id.replace("::", "_")
    node_id = node_id.replace("/", "_")
    log.debug("<== node_id_to_path node_id=%s" % node_id)
    return node_id


def make_tst_dir(path):
    tst_dir = get_tst_dir(path)
    if not os.path.exists(tst_dir):
        os.makedirs(tst_dir)


def write_file_to_tst_dir(name, path, text):
    file = open(f"{get_tst_dir(path)}/{name}", "w")
    file.write(text)
    file.close()


def get_tst_dir(path):
    tst_dir = f"logs/{path}" if path else "logs"
    return tst_dir


def open_log_file(name, path=None):
    make_tst_dir(path)
    logname = f"{get_tst_dir(path)}/{name}.log"
    log.debug("Using logname %s" % logname)
    logf = open(logname, 'w')
    return logf


def expect_prompt(shell, timeout=-1):
    log.debug("timeout=%s", timeout)
    shell.expect(r"\$|#", timeout=timeout)


def pexpect_shell(name, logfile_path=None, cd_to_dir=".", env=None):
    log.debug(f"name={name} logfile_path={logfile_path} cd_to_dir={cd_to_dir} env={env}")
    logf = open_log_file(name, logfile_path)
    shell = pexpect_spawn('/bin/bash --noprofile', sh_name=name)
    shell.logfile_send = logf
    shell.logfile_read = logf
    expect_prompt(shell)
    shell.sendline("PS1='\\u@\\h:\\w\\$ '")
    expect_prompt(shell)
    if cd_to_dir:
        shell.sendline(f"cd {cd_to_dir}")
        expect_prompt(shell)
    if env is not None:
        shell.sendline(env)
        expect_prompt(shell)
    return shell


def do_sleep(t, text=None):
    logtext = ""
    if text is not None:
        logtext = "(" + text + ") "
    log.debug("    sleep %d sec %s...", t, logtext)
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

class Pexpect(object):

    def __init__(self, shell = None, sh_name=None):
        log.debug("==> Pexpect __init__ shell=%r sh_name=%s" % (shell, sh_name))
        self.shell = shell
        self.sh_name = sh_name
        self._debug = False
        log.debug("<==")

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
        if not pytest.config.dryrun:
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

    def close(self, force=True):
        if not pytest.config.dryrun and self.shell is not None:
            try:
                self.shell.close(force)
            except:
                log.debug("    trying once more after 10 seconds...")
                do_sleep(10)
                try:
                    self.shell.close(force)
                except:
                    log.warning("Failed to close shell, IGNORING!")

    def send(self, s=''):
        log.debug("==> send %s", s)
        if self._debug:
            log.debug("    send: \"%s\"", self.sh_name )
        ret =  self.shell.send(s)
        log.debug("<== ret %s", ret)
        return ret

    def sendline(self, s=''):
        log.debug("==> sendline %s", s)
        #if "cli" in self.sh_name and self._debug:
        if self._debug:
            log.debug("    sendline: \"%s\"", self.sh_name)
        ret = self.shell.sendline(s)
        return ret

    def sendcontrol(self, char):
        if not pytest.config.dryrun:
            self.shell.sendcontrol(char)

    def flush(self):
        if not pytest.config.dryrun:
            self.shell.flush()

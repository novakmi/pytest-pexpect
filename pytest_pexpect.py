import logging
import os

import pexpect

logging.basicConfig(
    format='%(asctime)s:%(relativeCreated)s %(levelname)s:%(filename)s:%(lineno)s:%(funcName)s  %(message)s',
    level=logging.INFO)
log = logging.getLogger('pytest-expect')


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

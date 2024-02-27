from pytest_pexpect import Pexpect


def t_hello(pe: Pexpect):
    pe.make_shell("shell")
    pe.sendline('echo "Hello pexpect"')
    pe.expect('Hello pexpect', timeout=2)
    assert 1

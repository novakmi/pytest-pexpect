from pytest_pexpect import Pexpect, ShellParams


def t_shell_hello(pe_shell: Pexpect):
    pe_shell.sendline('echo "Hello pexpect"')
    pe_shell.expect('Hello pexpect', timeout=2)
    pe_shell.s('echo "Hello pexpect short"')
    pe_shell.e('Hello pexpect short', timeout=2)


def t_hello(pe: Pexpect):
    assert isinstance(pe, Pexpect)
    pe.make_shell(ShellParams(name="shell"))
    t_shell_hello(pe)

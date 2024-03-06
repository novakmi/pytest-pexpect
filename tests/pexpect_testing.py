from pytest_pexpect import Pexpect, ShellParams


def t_shell_hello(pe_shell: Pexpect):
    pe_shell.sendline('echo "Hello pexpect"')
    pe_shell.expect('Hello pexpect', timeout=2)


def t_hello(pe: Pexpect):
    pe.make_shell(ShellParams(name="shell"))
    t_shell_hello(pe)

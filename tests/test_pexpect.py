from pytest_pexpect import Pexpect
from pexpect_testing import t_hello, t_shell_hello


def test_pexpect(request):
    pe = Pexpect(request)
    t_hello(pe)


def test_pexpect_object(pexpect_object):
    t_hello(pexpect_object)


def test_pexpect_shell(pexpect_shell):
    t_shell_hello(pexpect_shell)


def test_make_pexpects(make_pexpects):
    pe = make_pexpects(1)
    t_hello(pe)

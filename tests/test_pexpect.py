from pexpect_testing import t_hello
from pytest_pexpect import Pexpect


def test_pexpect(request):
    pe = Pexpect(request)
    t_hello(pe)


def test_make_paexpect(make_pexpect):
    pe = make_pexpect(1)
    t_hello(pe)

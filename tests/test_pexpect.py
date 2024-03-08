import logging

import pytest
from pytest_pexpect import Pexpect, ShellParams
from pexpect_testing import t_hello, t_shell_hello

log = logging.getLogger(__name__)


def test_pexpect(request):
    pe = Pexpect(request)
    t_hello(pe)


def test_pexpect_object(pexpect_object):
    t_hello(pexpect_object)


@pytest.mark.parametrize("shell", [ShellParams()], ids=["default"])
def test_shell_default_parameters(pexpect_shell):
    assert isinstance(pexpect_shell, Pexpect)
    assert pexpect_shell.shell is not None
    assert pexpect_shell.name == "shell"
    assert pexpect_shell.shell.env is None
    t_shell_hello(pexpect_shell)


@pytest.mark.parametrize("shell", [
    ShellParams(name="shell_a", env="export PYTEST_TEST=yes_pexpect")],
                         ids=["custom"])
def test_shell_custom_parameters(pexpect_shell):
    assert isinstance(pexpect_shell, Pexpect)
    assert pexpect_shell.shell is not None
    assert pexpect_shell.name == "shell_a"
    t_shell_hello(pexpect_shell)
    pexpect_shell.sendline("echo $PYTEST_TEST")
    pexpect_shell.expect("yes_pexpect")


def test_make_pexpects(make_pexpects):
    pe = make_pexpects(1)
    t_hello(pe)


def test_does_not_make_pexpect_with_n_zero(make_pexpects):
    pe = make_pexpects(0)
    assert pe == ()


def test_make_multiple_pexpects(make_pexpects):
    pexpects = make_pexpects(3)
    assert isinstance(pexpects, tuple)
    assert len(pexpects) == 3
    for pe in pexpects:
        t_hello(pe)

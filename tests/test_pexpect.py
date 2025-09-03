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


def test_make_pexpects(pexpect_factory):
    pe = pexpect_factory()
    t_hello(pe)


def test_does_not_make_pexpect_with_n_zero(pexpect_factory):
    with pytest.raises(ValueError, match="Number of objects to create must be at least 1"):
        pexpect_factory(0)


def test_make_multiple_pexpects(pexpect_factory):
    pexpects = pexpect_factory(3)
    assert isinstance(pexpects, tuple)
    assert len(pexpects) == 3
    for pe in pexpects:
        t_hello(pe)


def test_factory_creates_single_shell(pexpect_factory):
    """Test creating a single shell-initialized object with pexpect_factory"""
    shell = pexpect_factory(shell_params=ShellParams(name="test_shell"))

    # Verify it's a shell-initialized Pexpect object
    assert isinstance(shell, Pexpect)
    assert shell.shell is not None
    assert shell.name == "test_shell"

    # Test basic shell functionality
    t_shell_hello(shell)


def test_factory_creates_multiple_shells_same_config(pexpect_factory):
    """Test creating multiple shell objects with same configuration"""
    shell_config = ShellParams(name="multi_shell", cd_to_dir="/tmp")
    shell1, shell2 = pexpect_factory(n=2, shell_params=shell_config)

    # Verify both are properly initialized
    assert isinstance(shell1, Pexpect)
    assert isinstance(shell2, Pexpect)
    assert shell1.shell is not None
    assert shell2.shell is not None
    assert shell1.name == "multi_shell"
    assert shell2.name == "multi_shell"

    # Test both shells work
    t_shell_hello(shell1)
    t_shell_hello(shell2)


def test_factory_creates_multiple_shells_different_configs(pexpect_factory):
    """Test creating multiple shell objects with different configurations"""
    params = [
        ShellParams(name="shell_a", cd_to_dir="/tmp"),
        ShellParams(name="shell_b", env="export TEST_VAR=hello"),
        ShellParams(name="shell_c", cd_to_dir="/home")
    ]
    shell_a, shell_b, shell_c = pexpect_factory(shell_params=params)

    # Verify all are properly initialized with correct names
    assert isinstance(shell_a, Pexpect)
    assert isinstance(shell_b, Pexpect)
    assert isinstance(shell_c, Pexpect)
    assert shell_a.name == "shell_a"
    assert shell_b.name == "shell_b"
    assert shell_c.name == "shell_c"

    # Test all shells work
    t_shell_hello(shell_a)
    t_shell_hello(shell_b)
    t_shell_hello(shell_c)

    # Test shell_b has the environment variable
    shell_b.sendline("echo $TEST_VAR", expect="hello")


def test_factory_shell_with_custom_directory(pexpect_factory):
    """Test shell creation with custom working directory"""
    shell = pexpect_factory(shell_params=ShellParams(name="dir_test", cd_to_dir="/tmp"))

    # Verify shell is in correct directory
    shell.sendline("pwd", expect="/tmp")


def test_factory_shell_with_environment(pexpect_factory):
    """Test shell creation with custom environment variables"""
    shell = pexpect_factory(shell_params=ShellParams(
        name="env_test",
        env="export CUSTOM_VAR=test_value"
    ))

    # Verify environment variable is set
    shell.sendline("echo $CUSTOM_VAR", expect="test_value")


def test_factory_validates_empty_shell_params_list(pexpect_factory):
    """Test that factory validates empty shell_params list"""
    with pytest.raises(ValueError, match="shell_params list cannot be empty"):
        pexpect_factory(shell_params=[])


def test_factory_mixed_shell_and_basic_objects(pexpect_factory):
    """Test creating both shell and basic objects in same test"""
    # Create a basic object
    basic_obj = pexpect_factory()
    assert isinstance(basic_obj, Pexpect)
    assert basic_obj.shell is None  # No shell initialized

    # Create a shell object
    shell_obj = pexpect_factory(shell_params=ShellParams(name="mixed_test"))
    assert isinstance(shell_obj, Pexpect)
    assert shell_obj.shell is not None  # Shell initialized
    assert shell_obj.name == "mixed_test"

    # Test shell functionality
    t_shell_hello(shell_obj)

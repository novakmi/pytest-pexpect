import logging.config

import pytest
from pytest_pexpect import (Pexpect, ShellParams,
                            PexpectForbiddenPatternException)

log = logging.getLogger(__name__)


def t_shell_hello(pe_shell: Pexpect):
    pe_shell.sendline('echo "Hello pexpect"')
    pe_shell.expect('Hello pexpect', timeout=2)
    pe_shell.expect_prompt()
    pe_shell.s('echo "Hello pexpect short"')
    pe_shell.e('Hello pexpect short', timeout=2)
    pe_shell.expect_prompt()
    pe_shell.sendline('echo "Hello pexpect combined"',
                      expect='Hello pexpect combined', timeout=2)
    pe_shell.expect_prompt()
    pe_shell.s('echo "Hello pexpect combined short"',
               expect='Hello pexpect combined short', timeout=2)
    pe_shell.expect_prompt()
    pe_shell.sendline('echo "Hello ok"')
    pe_shell.expect("Hello ok", forbidden_patterns=[],
                    timeout=2)
    pe_shell.expect_prompt()
    with pytest.raises(PexpectForbiddenPatternException) as e:
        pe_shell.sendline('echo "forbidden Hello"')
        pe_shell.expect("Hello", forbidden_patterns=["forbidden"],
                        timeout=2)
    log.debug("e.value=%s", e.value)
    assert "forbidden" in str(e.value)
    pe_shell.expect_prompt()


def t_hello(pe: Pexpect):
    assert isinstance(pe, Pexpect)
    pe.make_shell(ShellParams(name="shell"))
    t_shell_hello(pe)

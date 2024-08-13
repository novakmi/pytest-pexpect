import logging

log = logging.getLogger(__name__)


def test_pexpect_plugin(pytester):
    pytester.makepyfile("""
        from pytest_pexpect import Pexpect
        from pexpect_testing import *
        def test_pe(request):
            pe = Pexpect(request)
            t_hello(pe)
    """)
    pytester.copy_example("pexpect_testing.py")

    result = pytester.runpytest('-v')
    # TODO with debug level pytester.runpytest('-v') result is empty
    if not log.isEnabledFor(logging.DEBUG):
        # fnmatch_lines does an assertion internally
        result.stdout.fnmatch_lines([
            '*::test_pe PASSED*',
        ])
    else:
        log.warning("SKIPPING RESULT CHECK!")

    assert result.ret == 0

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

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_pe PASSED*',
    ])

    assert result.ret == 0

# def test_pexpect_plugin2(pytester):
#     pytester.copy_example("pexpect_testing.py")
#     pytester.copy_example("test_pexpect.py")
#     result = pytester.runpytest("-v", f"{pytester.path}")
#
#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines([
#         '*::test_pe PASSED*',
#     ])
#
#     assert result.ret == 0

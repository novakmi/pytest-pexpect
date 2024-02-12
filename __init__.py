from pytest_pexpect import (
    pytest_addoption,
    pytest_configure,
 )

# Note that plugins need to be listed here in order for pytest to pick them up
# when this package is installed.

__all__ = [
    # pytest_sessionfinish,
    pytest_addoption,
    pytest_configure,
    # pytest_collect_file,
]

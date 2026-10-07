"""Shared checks for installed-wheel and free-threaded test runs."""

import sys
import sysconfig
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--dist-dir", help="Validate the wheel and source archive in this directory")
    parser.addoption("--python-version", help="Require the intended Python major.minor version (for example 3.13t)")
    parser.addoption(
        "--python-variant", choices=("standard", "free-threaded"), help="Require the intended Python build variant"
    )


@pytest.fixture
def dist_dir(request):
    directory = request.config.getoption("--dist-dir")
    if directory is None:
        pytest.skip("Pass --dist-dir dist after uv build to validate distribution artifacts")
    return Path(directory).resolve()


def pytest_sessionstart(session):
    expected_version = session.config.getoption("--python-version")
    actual_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if expected_version and expected_version.removesuffix("t") != actual_version:
        pytest.exit(f"Expected Python {expected_version}, but selected Python {actual_version}", returncode=1)
    expected = session.config.getoption("--python-variant")
    actual = "free-threaded" if sysconfig.get_config_var("Py_GIL_DISABLED") else "standard"
    if expected and expected != actual:
        pytest.exit(f"Expected {expected} Python, but selected {actual} Python", returncode=1)
    if sysconfig.get_config_var("Py_GIL_DISABLED") and sys._is_gil_enabled():
        pytest.exit("The free-threaded interpreter must run with its GIL disabled", returncode=1)


def pytest_sessionfinish(session, exitstatus):
    # Check again after importing and exercising optional native dependencies.
    if sysconfig.get_config_var("Py_GIL_DISABLED") and sys._is_gil_enabled():
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter:
            reporter.write_sep("!", "A dependency enabled the GIL during the free-threaded test run", red=True)

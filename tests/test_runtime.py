"""Load the installed native framework on every supported Python runtime."""

import importlib.metadata
import sys
import sysconfig
from pathlib import Path

import objc
import pytest

import syphon


@pytest.mark.parametrize(
    "name",
    ["SyphonMetalServer", "SyphonMetalClient", "SyphonOpenGLServer", "SyphonOpenGLClient", "SyphonServerDirectory"],
)
def test_native_classes_are_available(name):
    assert getattr(syphon, name) is not None
    assert objc.lookUpClass(name) is not None


def test_framework_resources_are_installed():
    framework = Path(syphon.__file__).parent / "libs/Syphon.framework"
    for relative in ("Syphon", "Resources/Info.plist", "Resources/default.metallib", "Resources/License.txt"):
        assert (framework / relative).is_file(), relative
    assert importlib.metadata.version("syphon-python")


def test_free_threaded_runtime_does_not_enable_gil():
    if not sysconfig.get_config_var("Py_GIL_DISABLED"):
        pytest.skip("This is a regular CPython interpreter")
    assert not sys._is_gil_enabled()

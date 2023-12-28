"""
.. include:: ../README.md
.. include:: ../DOCUMENTATION.md
"""

from pathlib import Path

import objc

_SYPHON_LIBS_PATH = Path(__file__).parent.joinpath("libs")


def _load_lib_bundle(bundle_name: str, scan_classes: bool = False):
    """
    Load a dynamic library bundle using Objective-C.

    Parameters:
    - bundle_name (str): The name of the bundle to load.
    - scan_classes (bool, optional): If True, scan classes in the bundle. Defaults to False.
    """
    framework_path = _SYPHON_LIBS_PATH.joinpath(f"{bundle_name}.framework")
    objc.loadBundle(f"{bundle_name}", globals(), bundle_path=str(framework_path), scan_classes=scan_classes)


# initialize syphon bundle
_load_lib_bundle("Syphon")

from syphon.server import BaseSyphonServer, SyphonMetalServer, SyphonOpenGLServer
from syphon.server_directory import SyphonServerDirectory, SyphonServerNotification, SyphonServerDescription
from syphon.client import BaseSyphonClient, SyphonMetalClient, SyphonOpenGLClient
from pathlib import Path

import objc

SYPHON_LIBS_PATH = Path(__file__).parent.joinpath("libs")


def _load_lib_bundle(bundle_name: str, scan_classes: bool = False):
    framework_path = SYPHON_LIBS_PATH.joinpath(f"{bundle_name}.framework")
    objc.loadBundle(f"{bundle_name}", globals(), bundle_path=str(framework_path), scan_classes=scan_classes)


# initialize syphon bundle
_load_lib_bundle("Syphon")

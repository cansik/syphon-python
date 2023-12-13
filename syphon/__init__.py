from pathlib import Path

import objc

SYPHON_LIBS_PATH = Path(__file__).parent.joinpath("libs")


def load_syphon_bundle():
    syphon_framework_path = SYPHON_LIBS_PATH.joinpath("Syphon.framework")
    objc.loadBundle("Syphon", globals(), bundle_path=str(syphon_framework_path))


# initialize syphon bundle
load_syphon_bundle()

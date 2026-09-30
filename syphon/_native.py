"""Metadata and exported constants for the bundled Objective-C framework."""

from pathlib import Path

import objc
from Foundation import NSBundle

# NSOpenGLContext exposes an opaque pointer, not an Objective-C object. Register
# its wrapper so callbacks/constructors do not create untyped PyObjCPointers.
_CGLContextObj = objc.createOpaquePointerType("CGLContextObj", b"^{_CGLContextObject=}", "Opaque CGL context")

_bundle = NSBundle.bundleWithPath_(str(Path(__file__).parent / "libs/Syphon.framework"))
_options = {}
objc.loadBundleVariables(
    _bundle,
    _options,
    [
        (name, b"@")
        for name in (
            "SyphonServerOptionIsPrivate",
            "SyphonServerOptionAntialiasSampleCount",
            "SyphonServerOptionDepthBufferResolution",
            "SyphonServerOptionStencilBufferResolution",
        )
    ],
    skip_undefined=False,
)


def cgl_context(pointer):
    """Accept CGL pointers obtained before this module registered the opaque type."""
    if isinstance(pointer, objc.ObjCPointer) and pointer.typestr.startswith(b"^{_CGLContextObject"):
        return _CGLContextObj(c_void_p=pointer.pointerAsInteger)
    return pointer


def server_options(is_private=False, **options):
    """Translate supported option names using the framework's actual NSString values."""
    return {_options["SyphonServerOptionIsPrivate"]: bool(is_private), **{_options[k]: v for k, v in options.items()}}


for _class, _selector in (
    (b"SyphonMetalClient", b"initWithServerDescription:device:options:newFrameHandler:"),
    (b"SyphonOpenGLClient", b"initWithServerDescription:context:options:newFrameHandler:"),
):
    objc.registerMetaDataForSelector(
        _class,
        _selector,
        {
            "arguments": {
                5: {
                    "callable": {
                        "retval": {"type": b"v"},
                        "arguments": {0: {"type": b"^v"}, 1: {"type": b"@"}},
                    }
                }
            }
        },
    )

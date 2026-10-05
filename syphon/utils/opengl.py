from importlib import import_module
from typing import Any

import AppKit

from syphon.utils.exceptions import CGLContextNotFoundException, NSOpenGLContextNotFoundException

# Keep the public texture-target default available without importing PyOpenGL.
GL_TEXTURE_2D = 0x0DE1


def _require_pyopengl():
    try:
        return import_module("OpenGL.GL")
    except ModuleNotFoundError as exc:
        if exc.name not in {"OpenGL", "OpenGL.GL"}:
            raise
        raise ImportError(
            "OpenGL support requires PyOpenGL. Install it with: pip install 'syphon-python[opengl]'"
        ) from exc


def get_current_cgl_context_obj() -> Any:
    """
    Get the CGL context object for the current NSOpenGLContext.

    Returns:
    - Any: The CGL context object.

    Raises:
    - NSOpenGLContextNotFoundException: If the current NSOpenGLContext cannot be retrieved.
    - CGLContextNotFoundException: If the CGLContextObj cannot be retrieved from NSOpenGLContext.
    """
    ns_ctx = AppKit.NSOpenGLContext.currentContext()

    if ns_ctx is None:
        raise NSOpenGLContextNotFoundException()

    cgl_context = ns_ctx.CGLContextObj()

    if cgl_context is None:
        raise CGLContextNotFoundException()

    return cgl_context

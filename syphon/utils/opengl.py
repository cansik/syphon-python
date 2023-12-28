from typing import Any

import AppKit

from syphon.utils.exceptions import NSOpenGLContextNotFoundException, CGLContextNotFoundException


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

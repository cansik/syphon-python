from typing import Any

import AppKit


def get_current_cgl_context_obj() -> Any:
    """
    Get the CGL context object for the current NSOpenGLContext.

    Returns:
    - Any: The CGL context object.

    Raises:
    - Exception: If the current NSOpenGLContext cannot be retrieved.
                 Please first create a valid context or pass an existing one to the constructor.
    """
    ns_ctx = AppKit.NSOpenGLContext.currentContext()

    if ns_ctx is None:
        raise Exception("Could not read current NSOpenGLContext. "
                        "Please first create a valid context or pass an existing one to the constructor.")

    return ns_ctx.CGLContextObj()

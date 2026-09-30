"""Publish ten seconds of red frames by drawing directly into Syphon's framebuffer."""

import time

import AppKit
from OpenGL import GL

import syphon


def main():
    # Create an OpenGL context without opening a window.
    pixel_format = AppKit.NSOpenGLPixelFormat.alloc().initWithAttributes_(
        [
            AppKit.NSOpenGLPFAOpenGLProfile,
            AppKit.NSOpenGLProfileVersion3_2Core,
            AppKit.NSOpenGLPFAColorSize,
            24,
            AppKit.NSOpenGLPFAAlphaSize,
            8,
            AppKit.NSOpenGLPFAAccelerated,
            0,
        ]
    )
    if pixel_format is None:
        raise RuntimeError("No usable OpenGL pixel format")
    context = AppKit.NSOpenGLContext.alloc().initWithFormat_shareContext_(pixel_format, None)
    if context is None:
        raise RuntimeError("No usable OpenGL context")
    previous = AppKit.NSOpenGLContext.currentContext()
    context.makeCurrentContext()
    try:
        with (
            syphon.SyphonOpenGLServer("Direct OpenGL", antialias_sample_count=4, depth_buffer_resolution=24) as server,
            syphon.SyphonServerDirectory() as directory,
        ):
            directory.run_loop_interval = 0.001
            for _ in range(300):
                # Direct subsequent drawing into Syphon's framebuffer.
                if not server.bind_to_draw_frame((640, 480)):
                    raise RuntimeError("Could not bind the Syphon framebuffer")
                try:
                    # Fill the frame with opaque red.
                    GL.glViewport(0, 0, 640, 480)
                    GL.glClearColor(1, 0, 0, 1)
                    GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
                finally:
                    # Publish the frame and restore the framebuffer binding, even if drawing raises.
                    server.unbind_and_publish()
                # Keep this headless server discoverable by other applications.
                directory.update_run_loop()
                time.sleep(1 / 30)
    finally:
        if previous is not None:
            previous.makeCurrentContext()
        else:
            AppKit.NSOpenGLContext.clearCurrentContext()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

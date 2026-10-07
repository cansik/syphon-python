"""Exercise the native direct-rendering API with an offscreen OpenGL context."""

import threading
import time

import pytest

pytestmark = pytest.mark.opengl


@pytest.mark.parametrize("target", [0x0DE1, 0x84F5])
def test_texture_publish_queries_correct_target_and_preserves_query_binding(target):
    GL = pytest.importorskip("OpenGL.GL")
    import AppKit
    import objc

    import syphon

    with objc.autorelease_pool():
        fmt = AppKit.NSOpenGLPixelFormat.alloc().initWithAttributes_(
            [AppKit.NSOpenGLPFAOpenGLProfile, AppKit.NSOpenGLProfileVersion3_2Core, AppKit.NSOpenGLPFAColorSize, 24, 0]
        )
        context = None if fmt is None else AppKit.NSOpenGLContext.alloc().initWithFormat_shareContext_(fmt, None)
        if context is None:
            pytest.skip("No usable OpenGL context")
        previous = AppKit.NSOpenGLContext.currentContext()
        context.makeCurrentContext()
        textures = list(map(int, GL.glGenTextures(2)))
        try:
            texture, marker = textures
            GL.glBindTexture(target, texture)
            pixels = bytes((17, 53, 199, 255)) * 32
            GL.glTexImage2D(target, 0, GL.GL_RGBA8, 8, 4, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, pixels)
            GL.glTexParameteri(target, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
            GL.glBindTexture(target, marker)
            GL.glFinish()
            with syphon.SyphonOpenGLServer("Texture target test", is_private=True) as server:
                assert server._get_texture_size(texture, target=target) == (8, 4)
                binding = GL.GL_TEXTURE_BINDING_2D if target == GL.GL_TEXTURE_2D else GL.GL_TEXTURE_BINDING_RECTANGLE
                assert int(GL.glGetIntegerv(binding)) == marker
                server.publish_frame_texture(texture, target=target)
                GL.glFinish()
                output = server.new_frame_image
                assert tuple(output.textureSize()) == (8, 4)
                framebuffer = GL.glGenFramebuffers(1)
                previous_framebuffer = GL.glGetIntegerv(GL.GL_READ_FRAMEBUFFER_BINDING)
                try:
                    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, framebuffer)
                    GL.glFramebufferTexture2D(
                        GL.GL_READ_FRAMEBUFFER,
                        GL.GL_COLOR_ATTACHMENT0,
                        GL.GL_TEXTURE_RECTANGLE,
                        output.textureName(),
                        0,
                    )
                    GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
                    assert GL.glCheckFramebufferStatus(GL.GL_READ_FRAMEBUFFER) == GL.GL_FRAMEBUFFER_COMPLETE
                    assert bytes(GL.glReadPixels(0, 0, 8, 4, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)) == pixels
                finally:
                    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, previous_framebuffer)
                    GL.glDeleteFramebuffers(1, [framebuffer])
                    del output
        finally:
            GL.glDeleteTextures(textures)
            if previous is None:
                AppKit.NSOpenGLContext.clearCurrentContext()
            else:
                previous.makeCurrentContext()


@pytest.mark.parametrize("sample_count", [0, 4])
def test_direct_framebuffer_rendering(sample_count):
    GL = pytest.importorskip("OpenGL.GL")
    import AppKit
    import objc

    import syphon

    with objc.autorelease_pool():
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
            pytest.skip("No usable OpenGL pixel format")
        context = AppKit.NSOpenGLContext.alloc().initWithFormat_shareContext_(pixel_format, None)
        if context is None:
            pytest.skip("No usable OpenGL context")
        previous = AppKit.NSOpenGLContext.currentContext()
        context.makeCurrentContext()
        try:
            with syphon.SyphonOpenGLServer(
                "Direct render test",
                is_private=True,
                antialias_sample_count=sample_count,
                depth_buffer_resolution=24,
                stencil_buffer_resolution=8,
            ) as server:
                received = threading.Event()
                with syphon.SyphonOpenGLClient(
                    server.server_description, new_frame_handler=lambda _: received.set()
                ) as client:
                    deadline = time.monotonic() + 5
                    while not received.is_set() and time.monotonic() < deadline:
                        assert server.bind_to_draw_frame((8, 8))
                        try:
                            GL.glViewport(0, 0, 8, 8)
                            GL.glClearColor(1, 0, 0, 1)
                            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
                            if sample_count == 0:
                                pixels = GL.glReadPixels(0, 0, 8, 8, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
                                assert bytes(pixels) == bytes((255, 0, 0, 255)) * 64
                        finally:
                            server.unbind_and_publish()
                        received.wait(0.01)
                    assert received.is_set(), "OpenGL client received no frame notification"
                    frame = client.new_frame_image
                    assert frame is not None and tuple(frame.textureSize()) == (8, 8)
                    del frame
                image = server.new_frame_image
                assert image is not None
                assert tuple(image.textureSize()) == (8, 8)
                assert image.textureName() != 0
                GL.glBindTexture(GL.GL_TEXTURE_RECTANGLE, image.textureName())
                # Read IOSurface-backed textures through an FBO: the macOS driver
                # can return incomplete rows through glGetTexImage.
                framebuffer = GL.glGenFramebuffers(1)
                previous_framebuffer = GL.glGetIntegerv(GL.GL_READ_FRAMEBUFFER_BINDING)
                try:
                    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, framebuffer)
                    GL.glFramebufferTexture2D(
                        GL.GL_READ_FRAMEBUFFER,
                        GL.GL_COLOR_ATTACHMENT0,
                        GL.GL_TEXTURE_RECTANGLE,
                        image.textureName(),
                        0,
                    )
                    GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
                    assert GL.glCheckFramebufferStatus(GL.GL_READ_FRAMEBUFFER) == GL.GL_FRAMEBUFFER_COMPLETE
                    pixels = GL.glReadPixels(0, 0, 8, 8, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
                    assert bytes(pixels) == bytes((255, 0, 0, 255)) * 64
                finally:
                    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, previous_framebuffer)
                    GL.glDeleteFramebuffers(1, [framebuffer])
                GL.glBindTexture(GL.GL_TEXTURE_RECTANGLE, 0)
                # Drop the image while the owning context remains current.
                del image
        finally:
            if previous is not None:
                previous.makeCurrentContext()
            else:
                AppKit.NSOpenGLContext.clearCurrentContext()


def test_context_pointer_created_before_importing_syphon():
    import subprocess
    import sys
    import textwrap

    pytest.importorskip("OpenGL.GL")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent("""
            import AppKit
            import objc
            import warnings

            fmt = AppKit.NSOpenGLPixelFormat.alloc().initWithAttributes_([AppKit.NSOpenGLPFAColorSize, 24, 0])
            if fmt is None:
                raise SystemExit(77)
            ctx = AppKit.NSOpenGLContext.alloc().initWithFormat_shareContext_(fmt, None)
            if ctx is None:
                raise SystemExit(77)
            ctx.makeCurrentContext()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", objc.ObjCPointerWarning)
                pointer = ctx.CGLContextObj()
            import syphon
            try:
                with syphon.SyphonOpenGLServer("Legacy CGL pointer", pointer, is_private=True) as server:
                    with syphon.SyphonOpenGLClient(server.server_description, pointer) as client:
                        assert client.is_valid
                        assert client.cgl_context_obj is pointer
                        assert server.cgl_context_obj is pointer
            finally:
                AppKit.NSOpenGLContext.clearCurrentContext()
        """),
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode == 77:
        pytest.skip("No usable OpenGL context")
    assert result.returncode == 0, result.stdout + result.stderr

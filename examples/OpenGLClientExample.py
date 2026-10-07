from typing import Any

import glfw
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_QUADS,
    GL_TEXTURE_RECTANGLE,
    glBegin,
    glBindTexture,
    glClear,
    glClearColor,
    glDisable,
    glEnable,
    glEnd,
    glTexCoord2f,
    glVertex2f,
)

import syphon


def init_glfw(width: int, height: int):
    if not glfw.init():
        return

    window = glfw.create_window(width, height, "OpenGL Demo", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)

    # Enable vsync
    glfw.swap_interval(1)

    glClearColor(1, 0, 0, 1)

    return window


def render(texture: Any, width: int, height: int):
    glClear(GL_COLOR_BUFFER_BIT)

    glBindTexture(GL_TEXTURE_RECTANGLE, texture)
    glEnable(GL_TEXTURE_RECTANGLE)

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex2f(-1, -1)
    glTexCoord2f(width, 0)
    glVertex2f(1, -1)
    glTexCoord2f(width, height)
    glVertex2f(1, 1)
    glTexCoord2f(0, height)
    glVertex2f(-1, 1)
    glEnd()

    glDisable(GL_TEXTURE_RECTANGLE)
    glBindTexture(GL_TEXTURE_RECTANGLE, 0)


def main():
    window = init_glfw(640, 480)
    if window is None:
        return 1

    try:
        with syphon.SyphonServerDirectory() as directory:
            server = directory.wait_for_server(timeout=5)
            if server is None:
                print("No server found!")
                return 1

            with syphon.SyphonOpenGLClient(server) as client:
                while not glfw.window_should_close(window) and client.is_valid:
                    if client.has_new_frame:
                        image = client.new_frame_image
                        if image is not None:
                            try:
                                size = image.textureSize()
                                render(image.textureName(), int(size.width), int(size.height))
                            finally:
                                # Release while the OpenGL context is still current.
                                del image

                    glfw.poll_events()
                    glfw.swap_buffers(window)

        return 0
    finally:
        glfw.destroy_window(window)
        glfw.terminate()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass

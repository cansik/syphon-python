"""Publish a reusable OpenGL texture; close the window or press Ctrl+C to exit."""

import glfw
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_NEAREST,
    GL_QUADS,
    GL_RGBA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_UNSIGNED_BYTE,
    GLuint,
    glBegin,
    glBindTexture,
    glClear,
    glClearColor,
    glDeleteTextures,
    glEnable,
    glEnd,
    glGenTextures,
    glTexCoord2f,
    glTexImage2D,
    glTexParameteri,
    glTexSubImage2D,
    glVertex2f,
)

import syphon


def render(texture: GLuint, data: bytes, width: int, height: int):
    glClear(GL_COLOR_BUFFER_BIT)

    # Update the texture allocated once at startup.
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, data)

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex2f(-1, -1)
    glTexCoord2f(1, 0)
    glVertex2f(1, -1)
    glTexCoord2f(1, 1)
    glVertex2f(1, 1)
    glTexCoord2f(0, 1)
    glVertex2f(-1, 1)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)


def main():
    texture_width, texture_height = 640, 480

    if not glfw.init():
        return 1

    window = glfw.create_window(texture_width, texture_height, "OpenGL Demo", None, None)
    if not window:
        glfw.terminate()
        return 1

    glfw.make_context_current(window)

    texture = None
    try:
        with syphon.SyphonOpenGLServer("OpenGL Test") as server:
            glfw.swap_interval(1)
            glEnable(GL_TEXTURE_2D)

            # Allocate texture storage once and update its pixels for each frame.
            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, texture_width, texture_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
            glBindTexture(GL_TEXTURE_2D, 0)
            glClearColor(0, 0, 0, 1)

            value = 0
            print("publishing...")

            while not glfw.window_should_close(window):
                value = (value + 1) % 255
                pixels = bytes((value, 255 - value, 255, 255)) * (texture_width * texture_height)

                glfw.poll_events()
                render(texture, pixels, texture_width, texture_height)

                if server.has_clients:
                    server.publish_frame_texture(texture, size=(texture_width, texture_height))

                glfw.swap_buffers(window)

        return 0
    finally:
        if texture is not None:
            glDeleteTextures([texture])
        glfw.destroy_window(window)
        glfw.terminate()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass

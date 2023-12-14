from itertools import islice, cycle

import glfw
from OpenGL.GL import *
from OpenGL.GLUT import *

from syphon.server import SyphonOpenGLServer


def render(texture: GLuint, data: bytes, width: int, height: int):
    glClear(GL_COLOR_BUFFER_BIT)

    # Draw the numpy array image as a texture
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)

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
        return

    window = glfw.create_window(texture_width, texture_height, "OpenGL Demo", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)

    # start server
    syphon = SyphonOpenGLServer("Demo")

    # Enable vsync
    glfw.swap_interval(1)

    # create texture
    glEnable(GL_TEXTURE_2D)
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glBindTexture(GL_TEXTURE_2D, 0)

    glClearColor(0, 0, 0, 1)

    value = 0
    print("publishing...")
    while not glfw.window_should_close(window):
        # generate random pixels
        value = (value + 1) % 255
        pixels = bytes(islice(cycle([value, 255 - value, 255, 255]), texture_width * texture_height * 4))

        glfw.poll_events()
        render(texture, pixels, texture_width, texture_height)

        if syphon.has_clients:
            syphon.publish_frame_texture(texture)

        glfw.swap_buffers(window)

    syphon.stop()
    glfw.terminate()


if __name__ == "__main__":
    main()

from typing import Any

import glfw
from OpenGL.GL import *

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

    directory = syphon.SyphonServerDirectory()
    # servers = directory.servers_matching_name(app_name="Simple Server")
    servers = directory.servers

    if not servers:
        print("No server found!")
        exit(1)

    server = servers[0]

    client = syphon.SyphonOpenGLClient(server)

    while not glfw.window_should_close(window):
        if client.has_new_frame:
            legacy_surface_image = client.new_frame_image
            size = legacy_surface_image.textureSize()
            width, height = int(size.width), int(size.height)
            texture = legacy_surface_image.textureName()

            render(texture, width, height)

        glfw.poll_events()
        glfw.swap_buffers(window)

    client.stop()
    glfw.terminate()


if __name__ == "__main__":
    main()

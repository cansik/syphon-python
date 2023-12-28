from typing import Any

import syphon

server = syphon.SyphonMetalServer("Demo")
server = syphon.SyphonOpenGLServer("Demo")

import Metal

mtl_device = Metal.MTLCreateSystemDefaultDevice()
server = syphon.SyphonMetalServer("Demo", device=mtl_device)

mtl_command_queue = mtl_device.newCommandQueue()
server = syphon.SyphonMetalServer("Demo", device=mtl_device, command_queue=mtl_command_queue)

texture = ...  # MTLTexture or glTexture
server.publish_frame_texture(texture)

if not server.has_clients:
    server.stop()


def handler(event: Any):
    print("A new server has been announced.")


directory = syphon.SyphonServerDirectory()
directory.add_observer(syphon.SyphonServerNotification.Announce, handler)

directory.update_run_loop()
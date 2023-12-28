from typing import Any

import syphon

server = syphon.SyphonMetalServer("Demo")
objc_syphon_metal_server = server.context

print(dir(objc_syphon_metal_server))

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

# clients

# receive the first server description
directory = syphon.SyphonServerDirectory()
server = directory.servers[0]

# create a Metal client
client = syphon.SyphonMetalClient(server, device=mtl_device)

# create an OpenGL client
client = syphon.SyphonOpenGLClient(server)

if client.has_new_frame:
    texture = client.new_frame_image

client.stop()
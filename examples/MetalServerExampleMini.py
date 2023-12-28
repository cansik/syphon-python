import time

import numpy as np

import syphon
from syphon.utils.numpy import copy_image_to_mtl_texture
from syphon.utils.raw import create_mtl_texture

# create server and texture
server = syphon.SyphonMetalServer("Demo")
texture = create_mtl_texture(server.device, 512, 512)

# create texture data
texture_data = np.zeros((512, 512, 4), dtype=np.uint8)
texture_data[:, :, 0] = 255  # fill red
texture_data[:, :, 3] = 255  # fill alpha

while True:
    # copy texture data to texture and publish frame
    copy_image_to_mtl_texture(texture_data, texture)
    server.publish_frame_texture(texture)
    time.sleep(1)

server.stop()

import ctypes
from typing import Any

import Metal
import cv2
import numpy as np

import syphon


def read_raw_bytes(texture: Any) -> bytes:
    if texture.pixelFormat() != Metal.MTLPixelFormatBGRA8Unorm:
        raise Exception("Not correct pixel format")

    bytes_per_row = texture.width() * 4  # Assuming 4 bytes per pixel (e.g., RGBA8 format)
    bytes_per_image = bytes_per_row * texture.height()
    mipmap_level = 0
    slice_number = 0
    region = Metal.MTLRegionMake2D(0, 0, texture.width(), texture.height())

    # Create a buffer to hold the pixel data
    buffer = ctypes.create_string_buffer(bytes_per_image)

    # Use getBytes to copy the pixel data into the buffer
    texture.getBytes_bytesPerRow_bytesPerImage_fromRegion_mipmapLevel_slice_(buffer,
                                                                             bytes_per_row,
                                                                             bytes_per_image,
                                                                             region,
                                                                             mipmap_level,
                                                                             slice_number)

    # Create a Data object from the raw bytes
    raw_bytes = bytes(buffer.raw)
    return raw_bytes


def main():
    directory = syphon.SyphonServerDirectory()
    servers = directory.servers_matching_name(app_name="Simple Server")

    if not servers:
        print("No server found!")
        exit(1)

    server = servers[0]

    client = syphon.SyphonMetalClient(server)

    running = True
    while running:
        if client.has_new_frame:
            texture = client.new_frame_image
            data = read_raw_bytes(texture)

            image = np.frombuffer(data, dtype=np.uint8)
            image = image.reshape((texture.height(), texture.width(), 4))

            cv2.imshow("Image", image)
            cv2.waitKey(1)

    print("done")


if __name__ == "__main__":
    main()

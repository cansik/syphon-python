from itertools import islice, cycle

import Metal
import syphon


def main():
    print("starting server...")
    server = syphon.SyphonMetalServer("Metal Test")

    # create texture and load image onto texture
    texture_width, texture_height = 640, 480

    # Create Metal texture descriptor
    texture_descriptor = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
        Metal.MTLPixelFormatRGBA8Unorm, texture_width, texture_height, False
    )

    # Create a Metal texture using server internal device
    metal_texture = server.device.newTextureWithDescriptor_(texture_descriptor)

    region = Metal.MTLRegion((0, 0, 0), (texture_width, texture_height, 1))
    bytes_per_row = texture_width * 4

    # changing color value
    value = 0

    running = True
    print("publishing...")
    while running:
        # generate random pixels
        value = (value + 1) % 255
        pixels = bytes(islice(cycle([value, 255 - value, 255, 255]), texture_width * texture_height * 4))

        # copy pixels onto texture
        metal_texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
            region,
            0,  # mipmapLevel
            pixels,
            bytes_per_row
        )

        # publish texture
        server.publish_frame_texture(metal_texture)

    server.stop()


if __name__ == "__main__":
    main()

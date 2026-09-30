"""Publish Metal frames while servicing Cocoa discovery notifications."""

import time

import Metal

import syphon


def main():
    print("starting server...")
    with syphon.SyphonMetalServer("Metal Test") as server, syphon.SyphonServerDirectory() as directory:
        directory.run_loop_interval = 0.001

        # Describe the size and pixel format of the texture.
        width, height = 640, 480
        descriptor = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
            Metal.MTLPixelFormatRGBA8Unorm, width, height, False
        )
        # Create the texture on the server's Metal device.
        texture = server.device.newTextureWithDescriptor_(descriptor)
        region = Metal.MTLRegion((0, 0, 0), (width, height, 1))
        value = 0
        print("publishing... (Ctrl+C to stop)")
        while True:
            started = time.monotonic()

            # Fill the image with a changing RGBA color.
            value = (value + 1) % 255
            pixels = bytes((value, 255 - value, 255, 255)) * (width * height)

            # Copy the pixels onto the texture and publish it.
            texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(region, 0, pixels, width * 4)
            server.publish_frame_texture(texture)

            # Headless applications must service Cocoa notifications for discovery.
            directory.update_run_loop()

            # Limit publishing to approximately 60 frames per second.
            time.sleep(max(0, 1 / 60 - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

"""Minimal NumPy-to-Metal publisher with headless discovery support."""

import time

import numpy as np

import syphon
from syphon.utils.numpy import copy_image_to_mtl_texture
from syphon.utils.raw import create_mtl_texture


def main():
    with syphon.SyphonMetalServer("Demo") as server, syphon.SyphonServerDirectory() as directory:
        directory.run_loop_interval = 0.001

        # Create a Metal texture and an opaque red NumPy image.
        texture = create_mtl_texture(server.device, 512, 512)
        data = np.zeros((512, 512, 4), dtype=np.uint8)
        data[:, :, 0] = 255  # red
        data[:, :, 3] = 255  # alpha
        print("publishing... (Ctrl+C to stop)")
        while True:
            # Copy the image onto the texture and publish it.
            copy_image_to_mtl_texture(data, texture)
            server.publish_frame_texture(texture)

            # Process discovery requests even though there is no window.
            directory.update_run_loop()
            time.sleep(1 / 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

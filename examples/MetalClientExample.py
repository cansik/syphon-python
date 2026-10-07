"""Discover a server and display its frames; press Escape or Q to exit."""

import time

import cv2
import numpy as np

import syphon
from syphon.utils.numpy import copy_mtl_texture_to_image


def main():
    try:
        with syphon.SyphonServerDirectory() as directory:
            directory.run_loop_interval = 0.001

            # Wait for a server to announce itself before connecting.
            print("Waiting up to five seconds for a Syphon server...")
            server = directory.wait_for_server(timeout=5)
            if server is None:
                print("No server found. Start a server and try again.")
                return 1

            print(f"Connected to {server.app_name}: {server.name}. Press Escape or Q to exit.")

            with syphon.SyphonMetalClient(server) as client:
                image = None

                while client.is_valid:
                    directory.update_run_loop()

                    if client.has_new_frame:
                        # Retrieve the latest Metal texture.
                        texture = client.new_frame_image
                        if texture is not None:
                            # Reuse the image buffer until the sender changes dimensions.
                            shape = (texture.height(), texture.width(), 4)
                            if image is None or image.shape != shape:
                                image = np.empty(shape, dtype=np.uint8)

                            copy_mtl_texture_to_image(texture, out=image)
                            cv2.imshow("Image", image)

                    # Process UI events even when no new frame arrives.
                    if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                        break

                    time.sleep(0.001)

        return 0
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass

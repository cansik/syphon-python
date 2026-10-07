"""Overlap image preparation and Metal publishing; press Ctrl+C to stop."""

import time

import syphon
from syphon.utils.raw import copy_bytes_to_mtl_texture, create_mtl_texture


def main():
    with syphon.SyphonMetalServer("Metal Async") as server, syphon.SyphonServerDirectory() as directory:
        directory.run_loop_interval = 0.001

        # Alternate textures so one can be uploaded while the GPU reads the other.
        width, height = 640, 480
        textures = [create_mtl_texture(server.device, width, height) for _ in range(2)]
        pending = [None, None]
        slot = 0
        value = 0
        print("publishing asynchronously... (Ctrl+C to stop)")

        try:
            while True:
                started = time.monotonic()

                # Prepare the next image while previously submitted GPU work runs.
                value = (value + 1) % 255
                pixels = bytes((value, 255 - value, 255, 255)) * (width * height)

                # Wait only before overwriting a texture that is still in use.
                if pending[slot] is not None:
                    pending[slot].waitUntilCompleted()
                    pending[slot] = None

                copy_bytes_to_mtl_texture(pixels, textures[slot])

                # Keep the command buffer so we can synchronize this texture's reuse.
                buffer = server.command_queue.commandBuffer()
                server.publish_frame_texture(textures[slot], command_buffer=buffer, auto_commit=False)
                buffer.commit()
                pending[slot] = buffer
                slot = (slot + 1) % len(textures)

                directory.update_run_loop()

                time.sleep(max(0, 1 / 60 - (time.monotonic() - started)))
        finally:
            # Finish outstanding work before releasing textures and stopping the server.
            for buffer in pending:
                if buffer is not None:
                    buffer.waitUntilCompleted()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

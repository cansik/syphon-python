"""Receive frame notifications and process textures on the application thread."""

import threading
import time

import syphon


def main():
    available = threading.Event()
    with syphon.SyphonServerDirectory() as directory:
        directory.run_loop_interval = 0.01
        print("Waiting for a Syphon server; press Ctrl+C to stop.")
        while not (servers := directory.servers):
            time.sleep(0.01)
        # The native callback only signals; texture access and shutdown stay here.
        with syphon.SyphonMetalClient(servers[0], new_frame_handler=lambda _: available.set()) as client:
            while client.is_valid:
                directory.update_run_loop()
                if available.wait(0.01):
                    available.clear()
                    frame = client.new_frame_image
                    if frame is not None:
                        print(f"Frame: {frame.width()} x {frame.height()}")
                        del frame


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

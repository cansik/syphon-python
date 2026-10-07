"""Loop a video; press Space to rename the server, or Escape or Q to exit."""

import math
import time
from pathlib import Path

import cv2
import Metal
import numpy as np

import syphon
from syphon.utils.numpy import copy_image_to_mtl_texture
from syphon.utils.raw import create_mtl_texture


def main():
    path = Path(__file__).resolve().parents[1] / "media/pexels-gamol-8879031.mp4"
    video = cv2.VideoCapture(str(path))
    try:
        if not video.isOpened():
            print(f"Could not open video: {path}")
            return 1

        # Read the video's dimensions and frame rate.
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0:
            print("Video has invalid frame dimensions")
            return 1

        fps = video.get(cv2.CAP_PROP_FPS)
        fps = fps if math.isfinite(fps) and fps > 0 else 30

        with syphon.SyphonMetalServer("Metal Video") as server, syphon.SyphonServerDirectory() as directory:
            directory.run_loop_interval = 0.001

            # Reuse the texture and converted image storage for each frame.
            texture = create_mtl_texture(server.device, width, height, Metal.MTLPixelFormatBGRA8Unorm)
            bgra_frame = np.empty((height, width, 4), dtype=np.uint8)
            name_counter = 0
            print("publishing video... (Space to rename, Escape or Q to stop)")

            while True:
                started = time.monotonic()

                # Read the next frame, restarting the video at the end.
                success, frame = video.read()
                if not success:
                    video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    success, frame = video.read()
                    if not success:
                        print("Could not read a frame after rewinding the video")
                        return 1

                # Convert and upload the image, then publish the texture.
                cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA, dst=bgra_frame)
                copy_image_to_mtl_texture(bgra_frame, texture)
                server.publish_frame_texture(texture, is_flipped=True)

                directory.update_run_loop()
                cv2.imshow("Frame", frame)

                # Rename the running server without disconnecting its clients.
                key = cv2.waitKey(1) & 0xFF
                if key == ord(" "):
                    name_counter += 1
                    server.name = f"Metal Video {name_counter}"
                    print(f"Server renamed to {server.name}")
                elif key in (27, ord("q")):
                    break

                time.sleep(max(0, 1 / fps - (time.monotonic() - started)))

        return 0
    finally:
        video.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass

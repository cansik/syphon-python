import cv2

import syphon
from syphon.utils.numpy import copy_image_to_mtl_texture
from syphon.utils.raw import create_mtl_texture


def main():
    print("starting video server...")
    server = syphon.SyphonMetalServer("Metal Video")

    # start video and read width and height
    video = cv2.VideoCapture("media/pexels-gamol-8879031.mp4")
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # create metal texture
    texture = create_mtl_texture(server.device, width, height)

    running = True
    while running:
        success, frame = video.read()

        if not success:
            video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # copy data to texture
        bgra_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        copy_image_to_mtl_texture(bgra_frame, texture)

        # publish texture
        server.publish_frame_texture(texture, is_flipped=True)

        cv2.imshow("Frame", frame)
        cv2.waitKey(1)

    video.release()
    server.stop()


if __name__ == "__main__":
    main()

import cv2

import syphon
from syphon.utils.numpy import copy_mtl_texture_to_image


def main():
    directory = syphon.SyphonServerDirectory()
    servers = directory.servers

    if not servers:
        print("No server found!")
        exit(1)

    server = servers[0]

    client = syphon.SyphonMetalClient(server)

    running = True
    while running:
        if client.has_new_frame:
            texture = client.new_frame_image
            image = copy_mtl_texture_to_image(texture)

            cv2.imshow("Image", image)
            cv2.waitKey(1)

    client.stop()


if __name__ == "__main__":
    main()

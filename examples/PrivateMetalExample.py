"""Connect directly to a private server, without directory discovery."""

import time

import syphon
from syphon.utils.raw import copy_bytes_to_mtl_texture, create_mtl_texture


def main():
    with syphon.SyphonMetalServer("Private output", is_private=True) as server:
        texture = create_mtl_texture(server.device, 64, 64)
        copy_bytes_to_mtl_texture(bytes((255, 0, 0, 255)) * (64 * 64), texture)
        server.name = "Renamed private output"
        with syphon.SyphonMetalClient(server.server_description, server.device) as client:
            for _ in range(120):
                server.publish_frame_texture(texture)
                if client.has_new_frame:
                    frame = client.new_frame_image
                    if frame is not None:
                        print(f"Received from {server.name}: {frame.width()} x {frame.height()}")
                        del frame
                time.sleep(1 / 30)
        output = server.new_frame_image
        if output is not None:
            print(f"Server preview: {output.width()} x {output.height()}")
            del output


if __name__ == "__main__":
    main()

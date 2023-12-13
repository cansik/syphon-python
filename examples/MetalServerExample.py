import syphon.server


def main():
    server = syphon.server.SyphonMetalServer("Test")

    while True:
        pass
        # server.publish_frame_texture(None)


if __name__ == "__main__":
    main()

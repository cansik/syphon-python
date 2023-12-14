import syphon


def main():
    directory = syphon.SyphonServerDirectory()
    servers = directory.servers

    for server in servers:
        print(f"{server.app_name} ({server.uuid})")


if __name__ == "__main__":
    main()

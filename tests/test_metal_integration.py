"""Exercise the bundled framework on a real Metal device."""

import time

import pytest

pytestmark = pytest.mark.metal


@pytest.fixture
def server():
    import Metal
    import objc

    import syphon

    with objc.autorelease_pool():
        device = Metal.MTLCreateSystemDefaultDevice()
        if device is None:
            pytest.skip("A Metal device is required for native integration tests")
        server = syphon.SyphonMetalServer("Syphon integration test", device=device)
        assert server.context is not None
        try:
            yield server
        finally:
            server.stop()


def test_server_copies_mutable_name(server):
    from Cocoa import NSMutableString

    name = NSMutableString.stringWithString_("Original name")
    server.context.setName_(name)
    name.appendString_(" changed by caller")
    assert str(server.context.name()) == "Original name"


def test_metal_frames_continue_after_client_stops(server):
    import Metal

    import syphon
    from syphon.utils.raw import copy_bytes_to_mtl_texture, copy_mtl_texture_to_bytes, create_mtl_texture

    raw = server.context.serverDescription()
    description = syphon.SyphonServerDescription(
        uuid=str(raw["SyphonServerDescriptionUUIDKey"]),
        name=str(raw["SyphonServerDescriptionNameKey"]),
        app_name=str(raw["SyphonServerDescriptionAppNameKey"]),
        icon=None,
        raw=raw,
    )
    clients = []
    directory = syphon.SyphonServerDirectory()
    directory.run_loop_interval = 0.01
    texture = create_mtl_texture(server.device, 16, 16)

    def receive(client, rgba):
        pixels = bytes(rgba) * 256
        copy_bytes_to_mtl_texture(pixels, texture)
        assert copy_mtl_texture_to_bytes(texture) == pixels
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            server.publish_frame_texture(texture)
            directory.update_run_loop()
            if client.has_new_frame:
                frame = client.new_frame_image
                if frame is not None:
                    assert (frame.width(), frame.height()) == (16, 16)
                    assert frame.pixelFormat() == Metal.MTLPixelFormatBGRA8Unorm
                    expected = bytes((rgba[2], rgba[1], rgba[0], rgba[3])) * 256
                    if copy_mtl_texture_to_bytes(frame) == expected:
                        return
            time.sleep(0.01)
        pytest.fail("Timed out receiving the expected Metal frame")

    try:
        for _ in range(2):
            client = syphon.SyphonMetalClient(description, device=server.device)
            clients.append(client)
            assert client.is_valid
        for client in clients:
            receive(client, (17, 53, 199, 255))
        clients.pop(0).stop()
        receive(clients[0], (101, 203, 37, 255))
    finally:
        for client in clients:
            client.stop()

"""Exercise the bundled framework on a real Metal device."""

import time

import pytest

pytestmark = pytest.mark.metal


@pytest.mark.parametrize("auto_commit", [False, True])
@pytest.mark.parametrize("bgra", [False, True])
def test_native_transfer_reuse_and_submission(server, auto_commit, bgra):
    import Metal

    np = pytest.importorskip("numpy")
    from syphon.utils.numpy import copy_image_to_mtl_texture, copy_mtl_texture_to_image
    from syphon.utils.raw import copy_mtl_texture_to_buffer, copy_mtl_texture_to_bytes, create_mtl_texture

    pixel_format = Metal.MTLPixelFormatBGRA8Unorm if bgra else Metal.MTLPixelFormatRGBA8Unorm
    texture = create_mtl_texture(server.device, 3, 2, pixel_format)
    strided = np.arange(48, dtype=np.uint8).reshape(2, 6, 4)[:, ::2]
    out = np.empty((2, 3, 4), dtype=np.uint8)
    staging = bytearray(24)
    snapshot = None
    for image in (strided, np.ascontiguousarray(strided[:, ::-1])):
        copy_image_to_mtl_texture(image, texture)
        assert copy_mtl_texture_to_bytes(texture) == image.tobytes()
        assert copy_mtl_texture_to_buffer(texture, staging) is staging
        assert staging == image.tobytes()
        assert copy_mtl_texture_to_image(texture, out=out) is out
        np.testing.assert_array_equal(out, image)
        if snapshot is None:
            snapshot = copy_mtl_texture_to_image(texture)
        buffer = server.command_queue.commandBuffer()
        assert server.publish_frame_texture(texture, command_buffer=buffer, auto_commit=auto_commit) is None
        if not auto_commit:
            assert buffer.status() == Metal.MTLCommandBufferStatusNotEnqueued
            buffer.commit()
            buffer.waitUntilCompleted()
        else:
            assert buffer.status() == Metal.MTLCommandBufferStatusCompleted
        assert buffer.error() is None
        output = server.new_frame_image
        if output.storageMode() == Metal.MTLStorageModeManaged:
            sync = server.command_queue.commandBuffer()
            encoder = sync.blitCommandEncoder()
            encoder.synchronizeResource_(output)
            encoder.endEncoding()
            sync.commit()
            sync.waitUntilCompleted()
        expected = image if bgra else image[:, :, [2, 1, 0, 3]]
        np.testing.assert_array_equal(copy_mtl_texture_to_image(output), expected)
    np.testing.assert_array_equal(snapshot, strided)
    assert not np.array_equal(snapshot, out)


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
        server.name = "Renamed connected output"
        assert server.server_description.uuid == description.uuid
        assert all(client.is_valid for client in clients)
        for client in clients:
            receive(client, (41, 83, 167, 255))
        clients.pop(0).stop()
        receive(clients[0], (101, 203, 37, 255))
    finally:
        for client in clients:
            client.stop()


def test_private_server_callbacks_output_and_lifecycle():
    import threading

    import Metal

    import syphon
    from syphon.utils.raw import create_mtl_texture

    device = Metal.MTLCreateSystemDefaultDevice()
    if device is None:
        pytest.skip("A Metal device is required")
    main_thread = threading.get_ident()
    notifications = []
    errors = []
    received = threading.Event()

    def on_frame(client):
        try:
            notifications.append((client, threading.get_ident()))
            with pytest.raises(RuntimeError, match="native frame callback"):
                client.stop()
        except BaseException as error:
            errors.append(error)
        finally:
            received.set()

    with syphon.SyphonServerDirectory() as directory:
        directory.run_loop_interval = 0.001
        with syphon.SyphonMetalServer("Private integration", device=device, is_private=True) as server:
            server.name = "Private renamed"
            assert server.name == "Private renamed"
            assert server.server_description.name == "Private renamed"
            texture = create_mtl_texture(device, 8, 8)
            with syphon.SyphonMetalClient(server.server_description, device, new_frame_handler=on_frame) as client:
                deadline = time.monotonic() + 5
                while not received.is_set() and time.monotonic() < deadline:
                    server.publish_frame_texture(texture)
                    directory.update_run_loop()
                    time.sleep(0.01)
                assert received.is_set(), "Native callback did not arrive"
                assert not errors
                assert notifications[0][0] is client
                assert notifications[0][1] != main_thread
                assert client.is_valid
                output = server.new_frame_image
                assert output is not None and (output.width(), output.height()) == (8, 8)
                assert all(entry.uuid != server.server_description.uuid for entry in directory.servers)
            count = len(notifications)
            for _ in range(3):
                server.publish_frame_texture(texture)
                directory.update_run_loop()
            assert len(notifications) == count
            client.stop()
        server.stop()


def test_public_rename_and_observer_removal(server):
    import syphon

    changes = []
    with syphon.SyphonServerDirectory() as directory:
        found = directory.wait_for_server(timeout=5, name=server.name)
        assert found is not None and found.uuid == server.server_description.uuid
        assert any(entry.uuid == found.uuid for entry in directory.server_snapshot)
    with syphon.SyphonServerDirectory() as directory:
        directory.run_loop_interval = 0.01
        token = directory.add_observer(syphon.SyphonServerNotification.Update, lambda note: changes.append(note))
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if any(entry.uuid == server.server_description.uuid for entry in directory.servers):
                break
        else:
            pytest.fail("Server did not appear in discovery")
        server.name = "Live renamed server"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if any(
                entry.uuid == server.server_description.uuid and entry.name == server.name
                for entry in directory.servers
            ):
                break
        else:
            pytest.fail("Renamed server did not update discovery")
        assert changes
        directory.remove_observer(token)
        count = len(changes)
        server.name = "Renamed again"
        for _ in range(10):
            directory.update_run_loop()
        assert len(changes) == count


def test_async_native_frames_and_disconnect(server):
    import asyncio
    import threading

    import syphon
    from syphon.utils.raw import create_mtl_texture

    async def scenario():
        loop = asyncio.get_running_loop()
        callbacks = []
        directory = syphon.SyphonServerDirectory()
        directory.run_loop_interval = 0.001
        texture = create_mtl_texture(server.device, 8, 8)
        client = syphon.SyphonMetalClient(
            server.server_description,
            server.device,
            new_frame_handler=lambda _: callbacks.append(threading.get_ident()),
            callback_loop=loop,
        )
        publish = True

        async def produce_and_pump():
            while True:
                if publish:
                    server.publish_frame_texture(texture)
                directory.update_run_loop()
                await asyncio.sleep(0.01)

        producer = asyncio.create_task(produce_and_pump())
        try:
            await client.wait_for_frame(timeout=5)
            assert client.has_new_frame
            assert client.new_frame_image is not None
            await asyncio.sleep(0.03)
            assert callbacks and set(callbacks) == {threading.get_ident()}
            publish = False
            server.stop()
            deadline = loop.time() + 5
            while client.is_valid and loop.time() < deadline:
                await asyncio.sleep(0.01)
            with pytest.raises(ConnectionError):
                await client.wait_for_frame(timeout=1)
        finally:
            producer.cancel()
            with pytest.raises(asyncio.CancelledError):
                await producer
            client.stop()
            directory.close()

    asyncio.run(scenario())

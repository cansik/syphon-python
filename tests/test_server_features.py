"""Native option forwarding, live properties, framebuffer pairing and observer ownership."""

import threading
from unittest.mock import Mock

import pytest

from syphon._native import server_options
from syphon.server import BaseSyphonServer, SyphonMetalServer, SyphonOpenGLServer
from syphon.server_directory import SyphonServerDescription, SyphonServerDirectory, SyphonServerNotification


@pytest.fixture
def server():
    server = SyphonMetalServer.__new__(SyphonMetalServer)
    BaseSyphonServer.__init__(server, "Initial")
    server._finish_initialization(Mock())
    return server


def test_live_name_description_and_image(server):
    server.context.name.return_value = "Native name"
    assert server.name == "Native name"
    server.name = "Renamed"
    server.context.setName_.assert_called_once_with("Renamed")
    raw = {"SyphonServerDescriptionUUIDKey": "id", "private-key": 42}
    server.context.serverDescription.return_value = raw
    assert server.server_description == SyphonServerDescription("id", "", "", None, raw)
    assert server.server_description.raw is raw
    assert server.new_frame_image is server.context.newFrameImage.return_value
    server.stop()
    assert server.new_frame_image is None
    with pytest.raises(RuntimeError):
        server.name = "Stopped"


def test_server_context_cleanup_and_initialization_failure(server):
    with pytest.raises(ValueError):
        with server as entered:
            assert entered is server
            raise ValueError()
    server.stop()
    server.context.stop.assert_called_once()
    with pytest.raises(RuntimeError):
        server.__enter__()
    with pytest.raises(RuntimeError, match="create the server"):
        server._finish_initialization(None)


@pytest.mark.parametrize("kind", ["metal", "opengl"])
def test_server_constructor_options(monkeypatch, kind):
    import syphon.server as module

    native = Mock()
    monkeypatch.setattr(module.objc, "lookUpClass", lambda name: native)
    monkeypatch.setattr(module.opengl, "_require_pyopengl", Mock())
    if kind == "metal":
        device, queue = Mock(), Mock()
        server = SyphonMetalServer("Private", device, queue, is_private=True)
        native.alloc.return_value.initWithName_device_options_.assert_called_once_with(
            "Private", device, server_options(True)
        )
    else:
        context = object()
        server = SyphonOpenGLServer(
            "Private",
            context,
            is_private=True,
            antialias_sample_count=4,
            depth_buffer_resolution=24,
            stencil_buffer_resolution=8,
        )
        native.alloc.return_value.initWithName_context_options_.assert_called_once_with(
            "Private",
            context,
            server_options(
                True,
                SyphonServerOptionAntialiasSampleCount=4,
                SyphonServerOptionDepthBufferResolution=24,
                SyphonServerOptionStencilBufferResolution=8,
            ),
        )
    server.stop()


@pytest.mark.parametrize(
    "options",
    [
        {"antialias_sample_count": -1},
        {"antialias_sample_count": True},
        {"depth_buffer_resolution": 8},
        {"stencil_buffer_resolution": 24},
    ],
)
def test_invalid_opengl_options(monkeypatch, options):
    import syphon.server as module

    monkeypatch.setattr(module.opengl, "_require_pyopengl", Mock())
    with pytest.raises(ValueError):
        SyphonOpenGLServer("Invalid", object(), **options)


def test_framebuffer_pairing_and_thread_ownership():
    server = SyphonOpenGLServer.__new__(SyphonOpenGLServer)
    BaseSyphonServer.__init__(server, "GL")
    server._finish_initialization(Mock())
    with pytest.raises(RuntimeError, match="No Syphon"):
        server.unbind_and_publish()
    server.context.bindToDrawFrameOfSize_.return_value = False
    assert not server.bind_to_draw_frame((32, 16))
    with pytest.raises(RuntimeError):
        server.unbind_and_publish()
    server.context.bindToDrawFrameOfSize_.return_value = True
    assert server.bind_to_draw_frame((32, 16))
    with pytest.raises(RuntimeError, match="already bound"):
        server.bind_to_draw_frame((32, 16))
    with pytest.raises(RuntimeError, match="Unbind"):
        server.stop()
    errors = []

    def unbind():
        try:
            server.unbind_and_publish()
        except RuntimeError as error:
            errors.append(error)

    thread = threading.Thread(target=unbind)
    thread.start()
    thread.join()
    assert len(errors) == 1
    server.context.unbindAndPublish.assert_not_called()
    server.unbind_and_publish()
    server.context.unbindAndPublish.assert_called_once()
    server.stop()
    with pytest.raises(RuntimeError, match="stopped"):
        server.bind_to_draw_frame((32, 16))


def test_directory_owns_only_its_tokens_and_close_is_idempotent():
    directory = SyphonServerDirectory()
    directory._notification_center = Mock()
    first, second = object(), object()
    directory._notification_center.addObserverForName_object_queue_usingBlock_.side_effect = [first, second]
    assert directory.add_observer(SyphonServerNotification.Announce, Mock()) is first
    assert directory.add_observer(SyphonServerNotification.Retire, Mock()) is second
    directory.remove_observer(object())
    directory._notification_center.removeObserver_.assert_not_called()
    directory.remove_observer(first)
    directory.remove_observer(first)
    with directory:
        pass
    directory.close()
    assert [call.args[0] for call in directory._notification_center.removeObserver_.call_args_list] == [first, second]
    with pytest.raises(RuntimeError, match="closed"):
        directory.add_observer(SyphonServerNotification.Update, Mock())

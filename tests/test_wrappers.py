"""Check wrapper behavior without requiring a GPU or a running Syphon peer."""

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from syphon.server import SyphonMetalServer
from syphon.server_directory import SyphonServerDescription, SyphonServerDirectory, SyphonServerNotification


@pytest.mark.parametrize(
    "region,size,expected",
    [
        (None, None, ((0, 0, 16, 8), (16, 8))),
        (None, (7, 4), ((0, 0, 7, 4), (7, 4))),
        ((1, 2, 3, 4), None, ((1, 2, 3, 4), (16, 8))),
        ((1, 2, 3, 4), (7, 4), ((1, 2, 3, 4), (7, 4))),
    ],
)
def test_region_and_size_defaults(region, size, expected):
    server = SyphonMetalServer.__new__(SyphonMetalServer)
    texture = SimpleNamespace(width=lambda: 16, height=lambda: 8)
    assert server._prepare_region_and_size(texture, region, size) == expected


@pytest.mark.parametrize("external_buffer", [False, True])
@pytest.mark.parametrize("auto_commit", [False, True])
def test_metal_command_buffer_ownership(external_buffer, auto_commit):
    server = SyphonMetalServer.__new__(SyphonMetalServer)
    server.context = Mock()
    server.command_queue = Mock()
    buffer = Mock() if external_buffer else None
    texture = SimpleNamespace(width=lambda: 16, height=lambda: 8)
    assert (
        server.publish_frame_texture(
            texture,
            region=(1, 2, 3, 4),
            is_flipped=True,
            command_buffer=buffer,
            auto_commit=auto_commit,
        )
        is None
    )
    if external_buffer:
        server.command_queue.commandBuffer.assert_not_called()
    else:
        server.command_queue.commandBuffer.assert_called_once_with()
        buffer = server.command_queue.commandBuffer.return_value
    args = server.context.publishFrameTexture_onCommandBuffer_imageRegion_flipped_.call_args.args
    assert args[0] is texture
    assert args[1] is buffer
    assert tuple(args[2].origin) == (1, 2)
    assert tuple(args[2].size) == (3, 4)
    assert args[3] is True
    assert buffer.method_calls == ([call.commit(), call.waitUntilCompleted()] if auto_commit else [])


def test_metal_submission_default_waits_for_completion_and_returns_none():
    server = SyphonMetalServer.__new__(SyphonMetalServer)
    server.context = Mock()
    server.command_queue = Mock()
    texture = SimpleNamespace(width=lambda: 16, height=lambda: 8)
    assert server.publish_frame_texture(texture) is None
    buffer = server.command_queue.commandBuffer.return_value
    assert buffer.method_calls == [call.commit(), call.waitUntilCompleted()]


def test_metal_rejects_missing_command_buffer():
    server = SyphonMetalServer.__new__(SyphonMetalServer)
    server.context = Mock()
    server.command_queue = Mock()
    server.command_queue.commandBuffer.return_value = None
    texture = SimpleNamespace(width=lambda: 16, height=lambda: 8)
    with pytest.raises(RuntimeError, match="command buffer"):
        server.publish_frame_texture(texture)
    server.context.publishFrameTexture_onCommandBuffer_imageRegion_flipped_.assert_not_called()


@pytest.fixture
def descriptions():
    return [
        SyphonServerDescription("a", "Camera", "Studio", None, {}),
        SyphonServerDescription("b", "Output", "Studio", None, {}),
        SyphonServerDescription("c", "Camera", "Other", None, {}),
    ]


@pytest.mark.parametrize(
    "name,app_name,ids",
    [
        (None, None, []),
        ("Missing", None, []),
        ("Camera", None, ["a", "c"]),
        (None, "Studio", ["a", "b"]),
        ("Camera", "Studio", ["a", "b", "c"]),
    ],
)
def test_directory_filters_match_either_name_without_duplicates(descriptions, name, app_name, ids):
    directory = SimpleNamespace(servers=descriptions)
    matches = SyphonServerDirectory.servers_matching_name(directory, name, app_name)
    assert [description.uuid for description in matches] == ids


def test_directory_converts_native_descriptions():
    raw = {
        "SyphonServerDescriptionUUIDKey": "uuid",
        "SyphonServerDescriptionNameKey": "Camera",
        "SyphonServerDescriptionAppNameKey": "Studio",
        "SyphonServerDescriptionIconKey": None,
    }
    directory = SyphonServerDirectory.__new__(SyphonServerDirectory)
    directory.update_run_loop = Mock()
    directory._syphonServerDirectoryObjC = Mock()
    directory._syphonServerDirectoryObjC.sharedDirectory.return_value.servers.return_value = [raw]
    assert directory.servers == [SyphonServerDescription("uuid", "Camera", "Studio", None, raw)]
    directory.update_run_loop.assert_called_once_with()


def test_directory_registers_notification_handler():
    directory = SyphonServerDirectory()
    directory._notification_center = Mock()
    handler = Mock()
    directory.add_observer(SyphonServerNotification.Announce, handler)
    directory._notification_center.addObserverForName_object_queue_usingBlock_.assert_called_once_with(
        "SyphonServerAnnounceNotification", None, None, handler
    )

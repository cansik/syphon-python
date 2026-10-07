"""Examples must release native and GUI resources on exit and failed operations."""

import runpy
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

import syphon

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize("scenario", ["quit", "rename", "unopened", "empty", "conversion-error"])
def test_video_exit_and_failure_cleanup(monkeypatch, scenario):
    np = pytest.importorskip("numpy")
    cv2 = MagicMock()
    video = cv2.VideoCapture.return_value
    video.isOpened.return_value = scenario != "unopened"
    dimensions = {cv2.CAP_PROP_FRAME_WIDTH: 8, cv2.CAP_PROP_FRAME_HEIGHT: 4, cv2.CAP_PROP_FPS: 30}
    video.get.side_effect = dimensions.get
    video.read.return_value = (scenario != "empty", np.zeros((4, 8, 3), dtype=np.uint8))
    cv2.waitKey.side_effect = [ord(" "), ord(" "), ord("q")] if scenario == "rename" else [ord("q")]
    if scenario == "conversion-error":
        cv2.cvtColor.side_effect = RuntimeError("Conversion failed")
    monkeypatch.setitem(sys.modules, "cv2", cv2)
    server, directory = MagicMock(), MagicMock()
    server.__enter__.return_value = server
    directory.__enter__.return_value = directory
    monkeypatch.setattr(syphon, "SyphonMetalServer", lambda _: server)
    monkeypatch.setattr(syphon, "SyphonServerDirectory", lambda: directory)
    namespace = runpy.run_path(str(EXAMPLES / "MetalServerVideoExample.py"))
    namespace["main"].__globals__["create_mtl_texture"] = MagicMock()
    namespace["main"].__globals__["copy_image_to_mtl_texture"] = MagicMock()
    if scenario == "conversion-error":
        with pytest.raises(RuntimeError, match="Conversion failed"):
            namespace["main"]()
    else:
        assert namespace["main"]() == (0 if scenario in ("quit", "rename") else 1)
    video.release.assert_called_once_with()
    cv2.destroyAllWindows.assert_called_once_with()
    if scenario != "unopened":
        server.__exit__.assert_called_once()
        directory.__exit__.assert_called_once()
    if scenario == "empty":
        assert video.read.call_count == 2  # no busy loop on an unreadable video
    if scenario == "rename":
        assert server.name == "Metal Video 2"
        assert server.publish_frame_texture.call_count == 3
        assert cv2.waitKey.call_count == 3
        server.command_queue.commandBuffer.assert_not_called()


def test_minimal_image_example_uploads_every_frame(monkeypatch):
    pytest.importorskip("numpy")
    events = []
    server, directory = MagicMock(), MagicMock()
    server.__enter__.return_value = server
    directory.__enter__.return_value = directory
    server.publish_frame_texture.side_effect = lambda _: events.append("publish")
    directory.update_run_loop.side_effect = [None, KeyboardInterrupt]
    monkeypatch.setattr(syphon, "SyphonMetalServer", lambda _: server)
    monkeypatch.setattr(syphon, "SyphonServerDirectory", lambda: directory)
    namespace = runpy.run_path(str(EXAMPLES / "MetalServerExampleMini.py"))
    namespace["main"].__globals__["create_mtl_texture"] = Mock()
    namespace["main"].__globals__["copy_image_to_mtl_texture"] = Mock(side_effect=lambda *_: events.append("upload"))
    namespace["main"].__globals__["time"] = Mock()

    with pytest.raises(KeyboardInterrupt):
        namespace["main"]()

    assert events == ["upload", "publish", "upload", "publish"]
    server.__exit__.assert_called_once()


@pytest.mark.parametrize("upload_error", [False, True])
def test_async_example_synchronizes_texture_reuse_and_drains_on_exit(monkeypatch, upload_error):
    events = []
    textures = [object(), object()]
    buffers = [Mock() for _ in range(3)]
    for index, buffer in enumerate(buffers):
        buffer.commit.side_effect = lambda index=index: events.append(("commit", index))
        buffer.waitUntilCompleted.side_effect = lambda index=index: events.append(("wait", index))

    server, directory = MagicMock(), MagicMock()
    server.__enter__.return_value = server
    directory.__enter__.return_value = directory
    server.command_queue.commandBuffer.side_effect = buffers
    directory.update_run_loop.side_effect = [None, None, KeyboardInterrupt]
    monkeypatch.setattr(syphon, "SyphonMetalServer", lambda _: server)
    monkeypatch.setattr(syphon, "SyphonServerDirectory", lambda: directory)
    namespace = runpy.run_path(str(EXAMPLES / "MetalServerAsyncExample.py"))
    namespace["main"].__globals__["create_mtl_texture"] = Mock(side_effect=textures)
    namespace["main"].__globals__["time"] = Mock(monotonic=Mock(return_value=0))

    def upload(pixels, texture):
        if upload_error and events.count(("upload", 0)) == 1 and texture is textures[0]:
            raise RuntimeError("Upload failed")
        events.append(("upload", textures.index(texture)))

    def publish(texture, *, command_buffer, auto_commit):
        assert auto_commit is False
        events.append(("publish", textures.index(texture), buffers.index(command_buffer)))

    namespace["main"].__globals__["copy_bytes_to_mtl_texture"] = upload
    server.publish_frame_texture.side_effect = publish

    with pytest.raises(RuntimeError if upload_error else KeyboardInterrupt):
        namespace["main"]()

    expected = [
        ("upload", 0),
        ("publish", 0, 0),
        ("commit", 0),
        ("upload", 1),
        ("publish", 1, 1),
        ("commit", 1),
        ("wait", 0),
    ]
    if not upload_error:
        expected += [("upload", 0), ("publish", 0, 2), ("commit", 2), ("wait", 2)]
    assert events == expected + [("wait", 1)]
    server.__exit__.assert_called_once()
    directory.__exit__.assert_called_once()


def test_opengl_server_cleans_up_after_drawing_failure(monkeypatch):
    glfw, gl = MagicMock(), MagicMock()
    glfw.init.return_value = True
    glfw.window_should_close.return_value = False
    monkeypatch.setitem(sys.modules, "glfw", glfw)
    monkeypatch.setitem(sys.modules, "OpenGL", MagicMock())
    monkeypatch.setitem(sys.modules, "OpenGL.GL", gl)
    server = MagicMock()
    server.__enter__.return_value = server
    monkeypatch.setattr(syphon, "SyphonOpenGLServer", lambda _: server)
    namespace = runpy.run_path(str(EXAMPLES / "OpenGLServerExample.py"))
    namespace["main"].__globals__["render"] = MagicMock(side_effect=RuntimeError("Drawing failed"))
    with pytest.raises(RuntimeError, match="Drawing failed"):
        namespace["main"]()
    server.__exit__.assert_called_once()
    gl.glDeleteTextures.assert_called_once()
    glfw.destroy_window.assert_called_once_with(glfw.create_window.return_value)
    glfw.terminate.assert_called_once_with()


def test_opengl_client_cleans_up_when_no_server_is_found(monkeypatch):
    glfw = MagicMock()
    monkeypatch.setitem(sys.modules, "glfw", glfw)
    monkeypatch.setitem(sys.modules, "OpenGL", MagicMock())
    monkeypatch.setitem(sys.modules, "OpenGL.GL", MagicMock())
    directory = MagicMock()
    directory.__enter__.return_value = directory
    directory.wait_for_server.return_value = None
    monkeypatch.setattr(syphon, "SyphonServerDirectory", lambda: directory)
    main = runpy.run_path(str(EXAMPLES / "OpenGLClientExample.py"))["main"]
    assert main() == 1
    directory.__exit__.assert_called_once()
    glfw.destroy_window.assert_called_once_with(glfw.create_window.return_value)
    glfw.terminate.assert_called_once_with()

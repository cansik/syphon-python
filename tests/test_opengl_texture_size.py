"""Check target-aware size queries and state preservation without a GL context."""

from unittest.mock import Mock, call

import pytest

from syphon.server import SyphonOpenGLServer


@pytest.fixture
def gl(monkeypatch):
    from syphon.utils import opengl

    gl = Mock(
        GL_TEXTURE_2D=0x0DE1,
        GL_TEXTURE_RECTANGLE=0x84F5,
        GL_TEXTURE_BINDING_2D=0x8069,
        GL_TEXTURE_BINDING_RECTANGLE=0x84F6,
        GL_TEXTURE_WIDTH=0x1000,
        GL_TEXTURE_HEIGHT=0x1001,
    )
    gl.glGetIntegerv.return_value = 99
    gl.glGetTexLevelParameteriv.side_effect = [8, 4]
    monkeypatch.setattr(opengl, "_require_pyopengl", lambda: gl)
    return gl


@pytest.mark.parametrize("target,binding", [(0x0DE1, 0x8069), (0x84F5, 0x84F6)])
def test_publish_queries_requested_target_and_restores_binding(gl, target, binding):
    server = SyphonOpenGLServer.__new__(SyphonOpenGLServer)
    server.context = Mock()
    server.publish_frame_texture(7, target=target)
    gl.glGetIntegerv.assert_called_once_with(binding)
    assert gl.glGetTexLevelParameteriv.call_args_list == [
        call(target, 0, gl.GL_TEXTURE_WIDTH),
        call(target, 0, gl.GL_TEXTURE_HEIGHT),
    ]
    assert gl.glBindTexture.call_args_list == [call(target, 7), call(target, 99)]
    args = server.context.publishFrameTexture_textureTarget_imageRegion_textureDimensions_flipped_.call_args.args
    assert args[0:2] == (7, target)
    assert tuple(args[3]) == (8, 4)


def test_failed_query_restores_binding(gl):
    gl.glGetTexLevelParameteriv.side_effect = RuntimeError("Driver query failed")
    server = SyphonOpenGLServer.__new__(SyphonOpenGLServer)
    with pytest.raises(RuntimeError, match="Driver query failed"):
        server._get_texture_size(7)
    assert gl.glBindTexture.call_args_list == [call(gl.GL_TEXTURE_2D, 7), call(gl.GL_TEXTURE_2D, 99)]


def test_known_dimensions_skip_driver_queries(gl):
    server = SyphonOpenGLServer.__new__(SyphonOpenGLServer)
    server.context = Mock()
    server.publish_frame_texture(7, size=(8, 4), target=gl.GL_TEXTURE_RECTANGLE)
    gl.glGetIntegerv.assert_not_called()
    gl.glGetTexLevelParameteriv.assert_not_called()
    gl.glBindTexture.assert_not_called()

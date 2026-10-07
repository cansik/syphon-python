"""Keep the public API importable without loading the optional PyOpenGL package."""

import importlib.metadata
import inspect
import subprocess
import sys
import textwrap
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from packaging.requirements import Requirement


def test_import_and_errors_without_opengl():
    subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent("""\
                import importlib.abc
                import sys
                import typing
                from types import SimpleNamespace

                attempts = []
                class NoOpenGL(importlib.abc.MetaPathFinder):
                    def find_spec(self, fullname, path=None, target=None):
                        if fullname == "OpenGL" or fullname.startswith("OpenGL."):
                            attempts.append(fullname)
                            raise ModuleNotFoundError("PyOpenGL unavailable", name="OpenGL")

                sys.meta_path.insert(0, NoOpenGL())
                import syphon
                from syphon.client import SyphonMetalClient, SyphonOpenGLClient
                from syphon.server import SyphonMetalServer, SyphonOpenGLServer
                from syphon.utils import raw

                assert syphon.SyphonMetalServer is SyphonMetalServer
                assert syphon.SyphonMetalClient is SyphonMetalClient
                assert syphon.SyphonOpenGLServer is SyphonOpenGLServer
                assert syphon.SyphonOpenGLClient is SyphonOpenGLClient
                typing.get_type_hints(SyphonOpenGLServer.publish_frame_texture)
                assert not attempts, attempts
                assert not any(n == "OpenGL" or n.startswith("OpenGL.") for n in sys.modules)

                for construct in (
                    lambda: SyphonOpenGLServer("test"),
                    lambda: SyphonOpenGLServer("test", cgl_context_obj=object()),
                    lambda: SyphonOpenGLClient(SimpleNamespace(raw={})),
                    lambda: SyphonOpenGLClient(SimpleNamespace(raw={}), cgl_context_obj=object()),
                ):
                    try:
                        construct()
                    except ImportError as exc:
                        assert "pip install 'syphon-python[opengl]'" in str(exc)
                    else:
                        raise AssertionError("Expected a helpful missing-extra error")
            """),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_opengl_is_only_an_extra():
    requirements = [Requirement(value) for value in importlib.metadata.requires("syphon-python")]
    opengl = [requirement for requirement in requirements if requirement.name.lower() == "pyopengl"]
    assert len(opengl) == 1
    assert opengl[0].marker is not None
    assert not opengl[0].marker.evaluate({"extra": ""})
    assert opengl[0].marker.evaluate({"extra": "opengl"})


def test_unrelated_import_errors_are_preserved(monkeypatch):
    from syphon.utils import opengl

    error = ModuleNotFoundError("An internal dependency is missing", name="internal_dependency")
    monkeypatch.setattr(opengl, "import_module", Mock(side_effect=error))
    with pytest.raises(ModuleNotFoundError) as caught:
        opengl._require_pyopengl()
    assert caught.value is error


def test_opengl_publish_preserves_default_and_explicit_targets():
    from syphon.server import SyphonOpenGLServer

    publish = SyphonOpenGLServer.publish_frame_texture
    assert inspect.signature(publish).parameters["target"].default == 0x0DE1  # GL_TEXTURE_2D
    context = Mock()
    server = SimpleNamespace(context=context, _prepare_region_and_size=lambda *args: ((0, 0, 8, 4), (8, 4)))
    publish(server, 7)
    call = context.publishFrameTexture_textureTarget_imageRegion_textureDimensions_flipped_.call_args
    assert call.args[0:2] == (7, 0x0DE1)
    assert call.args[-1] is False
    publish(server, 9, size=(8, 4), target=0x84F5, is_flipped=True)  # GL_TEXTURE_RECTANGLE
    call = context.publishFrameTexture_textureTarget_imageRegion_textureDimensions_flipped_.call_args
    assert call.args[0:2] == (9, 0x84F5)
    assert call.args[-1] is True


def test_extra_loads_real_pyopengl():
    pytest.importorskip("OpenGL")
    from syphon.utils import opengl

    gl = opengl._require_pyopengl()
    assert int(gl.GL_TEXTURE_2D) == opengl.GL_TEXTURE_2D
    assert callable(gl.glBindTexture)

import threading
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import Cocoa
import Metal
import objc

from syphon._native import cgl_context, server_options
from syphon.server_directory import SyphonServerDescription
from syphon.types import Region, Size, Texture
from syphon.utils import opengl


class BaseSyphonServer(ABC):
    """
    Abstract base class for Syphon servers.

    Attributes:
    - name (str): The name of the Syphon server.
    """

    def __init__(self, name: str):
        """
        Initialize a BaseSyphonServer.

        Parameters:
        - name (str): The name of the Syphon server.
        """
        self._name = name
        self._lifecycle_lock = threading.RLock()
        self._stopped = False
        self._bound_thread = None
        self.context = None

    def _finish_initialization(self, context):
        if context is None:
            self._stopped = True
            raise RuntimeError("Syphon could not create the server")
        self.context = context

    @property
    def name(self) -> str:
        """The live native name; assignment updates discovery in other applications."""
        return self._name if self.context is None else self.context.name()

    @name.setter
    def name(self, value: str):
        with self._lifecycle_lock:
            if self._stopped:
                raise RuntimeError("Syphon server is stopped")
            self.context.setName_(value)

    @property
    def server_description(self) -> SyphonServerDescription:
        """Complete native connection metadata, also usable for private servers."""
        return SyphonServerDescription.from_native(self.context.serverDescription())

    @property
    def new_frame_image(self) -> Any:
        """Current server output, or None; keep it alive while in use. PyObjC owns releases."""
        with self._lifecycle_lock:
            return None if self._stopped else self.context.newFrameImage()

    def __enter__(self):
        with self._lifecycle_lock:
            if self._stopped:
                raise RuntimeError("Syphon server is stopped")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    @abstractmethod
    def publish_frame_texture(
        self, texture: Texture, region: Optional[Region] = None, size: Optional[Size] = None, is_flipped: bool = False
    ):
        """
        Publish a frame with the given texture.

        Parameters:
        - texture (Texture): The texture to publish.
        - region (Region, optional): The region of the texture to publish. Defaults to None.
        - size (Size, optional): The size of the texture. Defaults to None.
        - is_flipped (bool, optional): If True, the frame is flipped. Defaults to False.
        """
        pass

    @abstractmethod
    def publish(self):
        """
        Publish the frame.
        """
        pass

    def stop(self):
        """Stop once. An OpenGL framebuffer must be unbound first."""
        with self._lifecycle_lock:
            if self._stopped:
                return
            if self._bound_thread is not None:
                raise RuntimeError("Unbind and publish the OpenGL framebuffer before stopping")
            self._stopped = True
            context = self.context
        if context is not None:
            context.stop()

    @property
    @abstractmethod
    def has_clients(self) -> bool:
        """
        Check if the Syphon server has clients.

        Returns:
        - bool: True if there are clients, False otherwise.
        """
        pass

    @abstractmethod
    def _get_texture_size(self, texture: Texture) -> Size:
        """
        Get the size of the texture.

        Parameters:
        - texture (Texture): The texture.

        Returns:
        - Size: The size of the texture.
        """
        pass

    def _prepare_region_and_size(
        self, texture: Texture, region: Optional[Region] = None, size: Optional[Size] = None
    ) -> Tuple[Region, Size]:
        """
        Prepare the region and size for publishing.

        Parameters:
        - texture (Texture): The texture to publish.
        - region (Region, optional): The region of the texture to publish. Defaults to None.
        - size (Size, optional): The size of the texture. Defaults to None.

        Returns:
        - Tuple[Region, Size]: The prepared region and size.
        """
        size = self._get_texture_size(texture) if size is None else size
        if region is None:
            region = (0, 0, *size)
        return region, size


class SyphonMetalServer(BaseSyphonServer):
    """
    Syphon server for Metal-based rendering.

    Attributes:
    - name (str): The name of the Syphon server.
    - device (Any): The Metal device.
    - command_queue (Any): The Metal command queue.
    - context (Any): The Syphon-Metal context.
    """

    def __init__(
        self, name: str, device: Optional[Any] = None, command_queue: Optional[Any] = None, *, is_private: bool = False
    ):
        """
        Initialize a SyphonMetalServer.

        Parameters:
        - name (str): The name of the Syphon server.
        - device (Any, optional): The Metal device. If None, the default system device will be used.
        - command_queue (Any, optional): The Metal command queue. If None, a new command queue will be created.
        - is_private (bool): Hide the server from discovery; connect using server_description instead.
        """
        super().__init__(name)

        self.device = device
        self.command_queue = command_queue

        # setup device
        if self.device is None:
            self.device = Metal.MTLCreateSystemDefaultDevice()

        if self.device is None:
            raise RuntimeError("No Metal device is available")

        # setup command queue
        if self.command_queue is None:
            self.command_queue = self.device.newCommandQueue()

        if self.command_queue is None:
            raise RuntimeError("Could not create a Metal command queue")

        # setup syphon-metal context
        SyphonMetalServerObjC = objc.lookUpClass("SyphonMetalServer")
        self._finish_initialization(
            SyphonMetalServerObjC.alloc().initWithName_device_options_(name, self.device, server_options(is_private))
        )

    def publish_frame_texture(
        self,
        texture: Texture,
        region: Optional[Region] = None,
        size: Optional[Size] = None,
        is_flipped: bool = False,
        command_buffer: Optional[Any] = None,
        auto_commit: bool = True,
    ) -> None:
        """
        Publish a frame with the given Metal texture.

        Parameters:
        - texture (Texture): The Metal texture to publish.
        - region (Region, optional): The region of the texture to publish. Defaults to None.
        - size (Size, optional): The size of the texture. Defaults to None.
        - is_flipped (bool, optional): If True, the frame is flipped. Defaults to False.
        - command_buffer (Any, optional): The Metal command buffer. If None, a new command buffer will be created.
        - auto_commit (bool, optional): If True, commit the buffer and wait for GPU completion. Defaults to True.

        By default, publishing waits for GPU completion so the CPU can safely reuse
        the texture after this method returns. With auto_commit=False, pass a
        command_buffer and commit it yourself. Call waitUntilCompleted() before
        overwriting its texture from the CPU.
        """
        # create ns-region
        region, _ = self._prepare_region_and_size(texture, region, size)
        ns_region = Cocoa.NSRect((region[0], region[1]), (region[2], region[3]))

        # prepare command buffer if necessary
        if command_buffer is None:
            command_buffer = self.command_queue.commandBuffer()
        if command_buffer is None:
            raise RuntimeError("Could not create a Metal command buffer")

        # publish actual texture
        self.context.publishFrameTexture_onCommandBuffer_imageRegion_flipped_(
            texture, command_buffer, ns_region, is_flipped
        )
        # commit command buffer
        if auto_commit:
            command_buffer.commit()
            command_buffer.waitUntilCompleted()

    def publish(self):
        """
        Publish the frame.
        """
        self.context.publish()

    @property
    def has_clients(self) -> bool:
        """
        Check if the SyphonMetalServer has clients.

        Returns:
        - bool: True if there are clients, False otherwise.
        """
        return self.context.hasClients()

    def _get_texture_size(self, texture: Texture) -> Tuple[int, int]:
        """
        Get the size of the Metal texture.

        Parameters:
        - texture (Texture): The Metal texture.

        Returns:
        - Tuple[int, int]: The size of the texture.
        """
        return texture.width(), texture.height()


class SyphonOpenGLServer(BaseSyphonServer):
    """
    Syphon server for OpenGL-based rendering.

    Attributes:
    - name (str): The name of the Syphon server.
    - cgl_context_obj (Any): The CGL context object.
    - context (Any): The Syphon-OpenGL context.
    """

    def __init__(
        self,
        name: str,
        cgl_context_obj: Optional[Any] = None,
        *,
        is_private: bool = False,
        antialias_sample_count: int = 0,
        depth_buffer_resolution: int = 0,
        stencil_buffer_resolution: int = 0,
    ):
        """
        Initialize a SyphonOpenGLServer.

        Parameters:
        - name (str): The name of the Syphon server.
        - cgl_context_obj (Any, optional): The CGL context object. If None, the current context will be used.
        - is_private (bool): Hide the server from discovery; this is not access control.
        - antialias_sample_count (int): Requested multisample count, or zero to disable it.
        - depth_buffer_resolution (int): Requested depth bits: 0, 16, 24, or 32.
        - stencil_buffer_resolution (int): Requested stencil bits: 0, 1, 4, 8, or 16.

        Framebuffer options apply to bind_to_draw_frame/unbind_and_publish. The native
        driver may choose the nearest supported buffer configuration.
        """
        super().__init__(name)

        opengl._require_pyopengl()

        for label, value, allowed in (
            ("antialias_sample_count", antialias_sample_count, None),
            ("depth_buffer_resolution", depth_buffer_resolution, (0, 16, 24, 32)),
            ("stencil_buffer_resolution", stencil_buffer_resolution, (0, 1, 4, 8, 16)),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (allowed and value not in allowed):
                raise ValueError(f"Invalid {label}: {value}")

        # store CGL context object
        self.cgl_context_obj = opengl.get_current_cgl_context_obj() if cgl_context_obj is None else cgl_context_obj

        # create syphon gl server
        SyphonOpenGLServerObjC = objc.lookUpClass("SyphonOpenGLServer")
        self._finish_initialization(
            SyphonOpenGLServerObjC.alloc().initWithName_context_options_(
                name,
                cgl_context(self.cgl_context_obj),
                server_options(
                    is_private,
                    SyphonServerOptionAntialiasSampleCount=antialias_sample_count,
                    SyphonServerOptionDepthBufferResolution=depth_buffer_resolution,
                    SyphonServerOptionStencilBufferResolution=stencil_buffer_resolution,
                ),
            )
        )

    def bind_to_draw_frame(self, size: Size) -> bool:
        """Bind Syphon's framebuffer. Pair a successful bind with unbind_and_publish().

        Drawing, unbinding, and native context access require exclusive use of the CGL
        context by the calling thread. A failed bind must not be followed by unbinding.
        """
        if len(size) != 2 or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in size):
            raise ValueError("Frame size must contain two positive integers")
        with self._lifecycle_lock:
            if self._stopped:
                raise RuntimeError("Syphon server is stopped")
            if self._bound_thread is not None:
                raise RuntimeError("Syphon framebuffer is already bound")
            success = bool(self.context.bindToDrawFrameOfSize_(Cocoa.NSSize(*size)))
            if success:
                self._bound_thread = threading.current_thread()
            return success

    def unbind_and_publish(self):
        """Publish and unbind on the same thread that successfully bound the framebuffer."""
        with self._lifecycle_lock:
            if self._bound_thread is None:
                raise RuntimeError("No Syphon framebuffer is bound")
            if self._bound_thread is not threading.current_thread():
                raise RuntimeError("Unbind on the thread that bound the Syphon framebuffer")
            self.context.unbindAndPublish()
            self._bound_thread = None

    def publish_frame_texture(
        self,
        texture: int,
        region: Optional[Region] = None,
        size: Optional[Size] = None,
        is_flipped: bool = False,
        target: int = opengl.GL_TEXTURE_2D,
    ):
        """
        Publish a frame with the given OpenGL texture.

        Parameters:
        - texture (int): The OpenGL texture identifier to publish.
        - region (Region, optional): The region of the texture to publish. Defaults to None.
        - size (Size, optional): The size of the texture. Defaults to None.
        - is_flipped (bool, optional): If True, the frame is flipped. Defaults to False.
        - target (int, optional): The OpenGL texture target. Defaults to GL_TEXTURE_2D.
        """
        # create ns-region
        if size is None and target != opengl.GL_TEXTURE_2D:
            size = self._get_texture_size(texture, target=target)
        region, size = self._prepare_region_and_size(texture, region, size)
        ns_region = Cocoa.NSRect((region[0], region[1]), (region[2], region[3]))
        ns_size = Cocoa.NSSize(size[0], size[1])

        self.context.publishFrameTexture_textureTarget_imageRegion_textureDimensions_flipped_(
            texture, target, ns_region, ns_size, is_flipped
        )

    def publish(self):
        """
        Publish the frame.
        """
        self.context.publish()

    @property
    def has_clients(self) -> bool:
        """
        Check if the SyphonOpenGLServer has clients.

        Returns:
        - bool: True if there are clients, False otherwise.
        """
        return self.context.hasClients()

    def _get_texture_size(self, texture: Texture, target: int = opengl.GL_TEXTURE_2D) -> Size:
        """
        Get the size of the OpenGL texture.

        Parameters:
        - texture (Texture): The OpenGL texture.

        Returns:
        - Size: The size of the texture.
        """
        gl = opengl._require_pyopengl()
        bindings = {
            gl.GL_TEXTURE_2D: gl.GL_TEXTURE_BINDING_2D,
            gl.GL_TEXTURE_RECTANGLE: gl.GL_TEXTURE_BINDING_RECTANGLE,
        }
        if target not in bindings:
            raise ValueError("Texture target must be GL_TEXTURE_2D or GL_TEXTURE_RECTANGLE")
        previous = int(gl.glGetIntegerv(bindings[target]))
        try:
            gl.glBindTexture(target, texture)
            width = int(gl.glGetTexLevelParameteriv(target, 0, gl.GL_TEXTURE_WIDTH))
            height = int(gl.glGetTexLevelParameteriv(target, 0, gl.GL_TEXTURE_HEIGHT))
            return width, height
        finally:
            gl.glBindTexture(target, previous)

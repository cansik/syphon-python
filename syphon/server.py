from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any

import Cocoa
import Metal
import objc
from OpenGL.GL import *

from syphon.types import Texture, Region, Size
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
        self.name = name

    @abstractmethod
    def publish_frame_texture(self,
                              texture: Texture,
                              region: Optional[Region] = None,
                              size: Optional[Size] = None,
                              is_flipped: bool = False):
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

    @abstractmethod
    def stop(self):
        """
        Stop the Syphon server.
        """
        pass

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

    def _prepare_region_and_size(self,
                                 texture: Texture,
                                 region: Optional[Region] = None,
                                 size: Optional[Size] = None) -> Tuple[Region, Size]:
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

    def __init__(self,
                 name: str,
                 device: Optional[Any] = None,
                 command_queue: Optional[Any] = None):
        """
        Initialize a SyphonMetalServer.

        Parameters:
        - name (str): The name of the Syphon server.
        - device (Any, optional): The Metal device. If None, the default system device will be used.
        - command_queue (Any, optional): The Metal command queue. If None, a new command queue will be created.
        """
        super().__init__(name)

        self.device = device
        self.command_queue = command_queue

        # setup device
        if self.device is None:
            self.device = Metal.MTLCreateSystemDefaultDevice()

        # setup command queue
        if self.command_queue is None:
            self.command_queue = self.device.newCommandQueue()

        # setup syphon-metal context
        SyphonMetalServerObjC = objc.lookUpClass("SyphonMetalServer")
        self.context = SyphonMetalServerObjC.alloc().initWithName_device_options_(name, self.device, None)

    def publish_frame_texture(self,
                              texture: Texture,
                              region: Optional[Region] = None,
                              size: Optional[Size] = None,
                              is_flipped: bool = False,
                              command_buffer: Optional[Any] = None,
                              auto_commit: bool = True):
        """
        Publish a frame with the given Metal texture.

        Parameters:
        - texture (Texture): The Metal texture to publish.
        - region (Region, optional): The region of the texture to publish. Defaults to None.
        - size (Size, optional): The size of the texture. Defaults to None.
        - is_flipped (bool, optional): If True, the frame is flipped. Defaults to False.
        - command_buffer (Any, optional): The Metal command buffer. If None, a new command buffer will be created.
        - auto_commit (bool, optional): If True, the command buffer is committed automatically. Defaults to True.
        """
        # create ns-region
        region, _ = self._prepare_region_and_size(texture, region, size)
        ns_region = Cocoa.NSRect((region[0], region[1]), (region[2], region[3]))

        # prepare command buffer if necessary
        if command_buffer is None:
            command_buffer = self.command_queue.commandBuffer()

        # publish actual texture
        self.context.publishFrameTexture_onCommandBuffer_imageRegion_flipped_(texture,
                                                                              command_buffer,
                                                                              ns_region,
                                                                              is_flipped)
        # commit command buffer
        if auto_commit:
            command_buffer.commitAndWaitUntilSubmitted()

    def publish(self):
        """
        Publish the frame.
        """
        self.context.publish()

    def stop(self):
        """
        Stop the SyphonMetalServer.
        """
        self.context.stop()

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

    def __init__(self, name: str, cgl_context_obj: Optional[Any] = None):
        """
        Initialize a SyphonOpenGLServer.

        Parameters:
        - name (str): The name of the Syphon server.
        - cgl_context_obj (Any, optional): The CGL context object. If None, the current context will be used.
        """
        super().__init__(name)

        # store CGL context object
        self.cgl_context_obj = opengl.get_current_cgl_context_obj() if cgl_context_obj is None else cgl_context_obj

        # create syphon gl server
        SyphonOpenGLServerObjC = objc.lookUpClass("SyphonOpenGLServer")
        self.context = SyphonOpenGLServerObjC.alloc().initWithName_context_options_(name, self.cgl_context_obj, None)

    def publish_frame_texture(self,
                              texture: GLint,
                              region: Optional[Region] = None,
                              size: Optional[Size] = None,
                              is_flipped: bool = False,
                              target: GLenum = GL_TEXTURE_2D):
        """
        Publish a frame with the given OpenGL texture.

        Parameters:
        - texture (GLint): The OpenGL texture to publish.
        - region (Region, optional): The region of the texture to publish. Defaults to None.
        - size (Size, optional): The size of the texture. Defaults to None.
        - is_flipped (bool, optional): If True, the frame is flipped. Defaults to False.
        - target (GLenum, optional): The OpenGL texture target. Defaults to GL_TEXTURE_2D.
        """
        # create ns-region
        region, size = self._prepare_region_and_size(texture, region, size)
        ns_region = Cocoa.NSRect((region[0], region[1]), (region[2], region[3]))
        ns_size = Cocoa.NSSize(size[0], size[1])

        self.context.publishFrameTexture_textureTarget_imageRegion_textureDimensions_flipped_(texture, target,
                                                                                              ns_region,
                                                                                              ns_size, is_flipped)

    def publish(self):
        """
        Publish the frame.
        """
        self.context.publish()

    def stop(self):
        """
        Stop the SyphonOpenGLServer.
        """
        self.context.stop()

    @property
    def has_clients(self) -> bool:
        """
        Check if the SyphonOpenGLServer has clients.

        Returns:
        - bool: True if there are clients, False otherwise.
        """
        return self.context.hasClients()

    def _get_texture_size(self, texture: Texture) -> Size:
        """
        Get the size of the OpenGL texture.

        Parameters:
        - texture (Texture): The OpenGL texture.

        Returns:
        - Size: The size of the texture.
        """
        glBindTexture(GL_TEXTURE_2D, texture)

        width = GLint()
        height = GLint()

        glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_WIDTH, width)
        glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_HEIGHT, height)

        glBindTexture(GL_TEXTURE_2D, 0)

        return int(width.value), int(height.value)

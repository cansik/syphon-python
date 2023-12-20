from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any

import Cocoa
import Metal
import objc
from OpenGL.GL import *

from syphon.types import Texture, Region, Size
from syphon.utils import opengl


class BaseSyphonServer(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def publish_frame_texture(self,
                              texture: Texture,
                              region: Optional[Region] = None,
                              size: Optional[Size] = None,
                              is_flipped: bool = False):
        pass

    @abstractmethod
    def publish(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @property
    @abstractmethod
    def has_clients(self) -> bool:
        pass

    @abstractmethod
    def _get_texture_size(self, texture: Texture) -> Size:
        pass

    def _prepare_region_and_size(self,
                                 texture: Texture,
                                 region: Optional[Region] = None,
                                 size: Optional[Size] = None) -> Tuple[Region, Size]:
        size = self._get_texture_size(texture) if size is None else size
        if region is None:
            region = (0, 0, *size)
        return region, size


class SyphonMetalServer(BaseSyphonServer):

    def __init__(self,
                 name: str,
                 device: Optional[Any] = None,
                 command_queue: Optional[Any] = None):
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
        self.context.publish()

    def stop(self):
        self.context.stop()

    @property
    def has_clients(self) -> bool:
        return self.context.hasClients()

    def _get_texture_size(self, texture: Texture) -> Tuple[int, int]:
        return texture.width(), texture.height()


class SyphonOpenGLServer(BaseSyphonServer):
    def __init__(self, name: str, cgl_context_obj: Optional[Any] = None):
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
        # create ns-region
        region, size = self._prepare_region_and_size(texture, region, size)
        ns_region = Cocoa.NSRect((region[0], region[1]), (region[2], region[3]))
        ns_size = Cocoa.NSSize(size[0], size[1])

        self.context.publishFrameTexture_textureTarget_imageRegion_textureDimensions_flipped_(texture, target,
                                                                                              ns_region,
                                                                                              ns_size, is_flipped)

    def publish(self):
        self.context.publish()

    def stop(self):
        self.context.stop()

    @property
    def has_clients(self) -> bool:
        return self.context.hasClients()

    def _get_texture_size(self, texture: Texture) -> Size:
        glBindTexture(GL_TEXTURE_2D, texture)

        width = GLint()
        height = GLint()

        glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_WIDTH, width)
        glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_HEIGHT, height)

        glBindTexture(GL_TEXTURE_2D, 0)

        return int(width.value), int(height.value)

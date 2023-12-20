from abc import ABC, abstractmethod
from typing import Optional, Any

import Metal
import objc

from syphon.server_directory import SyphonServerDescription
from syphon.utils import opengl


class BaseSyphonClient(ABC):

    def __init__(self, description: SyphonServerDescription):
        # todo: implement new frame handler callback support
        self._description = description

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        pass

    @property
    @abstractmethod
    def has_new_frame(self) -> bool:
        pass

    @abstractmethod
    def stop(self):
        pass


class SyphonMetalClient(BaseSyphonClient):

    def __init__(self, description: SyphonServerDescription, device: Optional[Any] = None, ):
        super().__init__(description)

        self.device = device

        # setup device
        if self.device is None:
            self.device = Metal.MTLCreateSystemDefaultDevice()

        # setup syphon-metal context
        SyphonMetalClientObjC = objc.lookUpClass("SyphonMetalClient")

        self.context = (
            SyphonMetalClientObjC
            .alloc()
            .initWithServerDescription_device_options_newFrameHandler_(
                description.raw,
                self.device,
                None,
                None)
        )

    @property
    def is_valid(self) -> bool:
        return self.context.isValid()

    @property
    def has_new_frame(self) -> bool:
        return self.context.hasNewFrame()

    @property
    def new_frame_image(self) -> Any:
        return self.context.newFrameImage()

    def stop(self):
        self.context.stop()


class SyphonOpenGLClient(BaseSyphonClient):

    def __init__(self, description: SyphonServerDescription, cgl_context_obj: Optional[Any] = None):
        super().__init__(description)

        # store CGL context object
        self.cgl_context_obj = opengl.get_current_cgl_context_obj() if cgl_context_obj is None else cgl_context_obj

        # create syphon gl client
        SyphonOpenGLClientObjC = objc.lookUpClass("SyphonOpenGLClient")
        self.context = (
            SyphonOpenGLClientObjC
            .alloc()
            .initWithServerDescription_context_options_newFrameHandler_(
                description.raw,
                self.cgl_context_obj,
                None,
                None)
        )

    @property
    def is_valid(self) -> bool:
        return self.context.isValid()

    @property
    def has_new_frame(self) -> bool:
        return self.context.hasNewFrame()

    @property
    def new_frame_image(self) -> Any:
        return self.context.newFrameImage()

    def stop(self):
        self.context.stop()

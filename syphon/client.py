from abc import ABC, abstractmethod
from typing import Optional, Any

import Metal
import objc

from syphon.server_directory import SyphonServerDescription
from syphon.utils import opengl


class BaseSyphonClient(ABC):
    """
    Abstract base class for Syphon clients.

    Attributes:
    - description (SyphonServerDescription): The description of the Syphon server.
    """

    def __init__(self, description: SyphonServerDescription):
        """
        Initialize a BaseSyphonClient.

        Parameters:
        - description (SyphonServerDescription): The description of the Syphon server.
        """
        # todo: implement new frame handler callback support
        self._description = description

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """
        Check if the Syphon client is valid.

        Returns:
        - bool: True if the client is valid, False otherwise.
        """
        pass

    @property
    @abstractmethod
    def has_new_frame(self) -> bool:
        """
        Check if the Syphon client has a new frame.

        Returns:
        - bool: True if there is a new frame, False otherwise.
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Stop the Syphon client.
        """
        pass


class SyphonMetalClient(BaseSyphonClient):
    """
    Syphon client for Metal-based rendering.

    Attributes:
    - description (SyphonServerDescription): The description of the Syphon server.
    - device (Any): The Metal device.
    - context (Any): The Syphon-Metal context.
    """

    def __init__(self, description: SyphonServerDescription, device: Optional[Any] = None):
        """
        Initialize a SyphonMetalClient.

        Parameters:
        - description (SyphonServerDescription): The description of the Syphon server.
        - device (Any, optional): The Metal device. If None, the default system device will be used.
        """
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
        """
        Check if the SyphonMetalClient is valid.

        Returns:
        - bool: True if the client is valid, False otherwise.
        """
        return self.context.isValid()

    @property
    def has_new_frame(self) -> bool:
        """
        Check if the SyphonMetalClient has a new frame.

        Returns:
        - bool: True if there is a new frame, False otherwise.
        """
        return self.context.hasNewFrame()

    @property
    def new_frame_image(self) -> Any:
        """
        Get the new frame image.

        Returns:
        - Any: The new frame image.
        """
        return self.context.newFrameImage()

    def stop(self):
        """
        Stop the SyphonMetalClient.
        """
        self.context.stop()


class SyphonOpenGLClient(BaseSyphonClient):
    """
    Syphon client for OpenGL-based rendering.

    Attributes:
    - description (SyphonServerDescription): The description of the Syphon server.
    - cgl_context_obj (Any): The CGL context object.
    - context (Any): The Syphon-OpenGL context.
    """

    def __init__(self, description: SyphonServerDescription, cgl_context_obj: Optional[Any] = None):
        """
        Initialize a SyphonOpenGLClient.

        Parameters:
        - description (SyphonServerDescription): The description of the Syphon server.
        - cgl_context_obj (Any, optional): The CGL context object. If None, the current context will be used.
        """
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
        """
        Check if the SyphonOpenGLClient is valid.

        Returns:
        - bool: True if the client is valid, False otherwise.
        """
        return self.context.isValid()

    @property
    def has_new_frame(self) -> bool:
        """
        Check if the SyphonOpenGLClient has a new frame.

        Returns:
        - bool: True if there is a new frame, False otherwise.
        """
        return self.context.hasNewFrame()

    @property
    def new_frame_image(self) -> Any:
        """
        Get the new frame image.

        Returns:
        - Any: The new frame image.
        """
        return self.context.newFrameImage()

    def stop(self):
        """
        Stop the SyphonOpenGLClient.
        """
        self.context.stop()

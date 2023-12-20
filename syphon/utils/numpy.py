from typing import Any

import numpy as np

from syphon.utils.raw import copy_mtl_texture_to_bytes, copy_bytes_to_mtl_texture


def copy_image_to_mtl_texture(image: np.ndarray, texture: Any):
    """
    Copy pixel data from a NumPy array representing an image to a Metal texture.

    Parameters:
    - image (np.ndarray): The input image as a NumPy array of shape (m, n, 4).
    - texture (Any): The target Metal texture to copy the image data into.

    Raises:
    - AssertionError: If the input image has an incorrect shape or number of channels.
    """
    assert len(image.shape) == 3, "Image has to be of shape (m, n, 4)"
    assert image.shape[2] == 4, "Image has to be of shape (m, n, 4)"

    data = image.tobytes()
    copy_bytes_to_mtl_texture(data, texture)


def copy_mtl_texture_to_image(texture: Any) -> np.ndarray:
    """
    Copy pixel data from a Metal texture to a NumPy array representing an image.

    Parameters:
    - texture (Any): The source Metal texture to copy pixel data from.

    Returns:
    - np.ndarray: The resulting image as a NumPy array of shape (height, width, 4).
    
    Note:
    - todo: Add support for buffer re-use.
    """
    # todo: support buffer re-use
    data = copy_mtl_texture_to_bytes(texture)
    image = np.frombuffer(data, dtype=np.uint8)
    return image.reshape((texture.height(), texture.width(), 4))

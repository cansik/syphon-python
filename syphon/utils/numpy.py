from typing import Any

import numpy as np
from numpy.typing import NDArray

from syphon.utils.raw import copy_bytes_to_mtl_texture, copy_mtl_texture_to_buffer


def copy_image_to_mtl_texture(image: np.ndarray, texture: Any) -> None:
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

    # Preserve subclass serialization (e.g. masked arrays) and uncommon dtypes.
    borrow = type(image) is np.ndarray and image.dtype == np.uint8 and image.flags.c_contiguous
    data = memoryview(image) if borrow else image.tobytes()
    copy_bytes_to_mtl_texture(data, texture)


def copy_mtl_texture_to_image(texture: Any, out: NDArray[np.uint8] | None = None) -> NDArray[np.uint8]:
    """
    Copy pixel data from a Metal texture to a NumPy array representing an image.

    Parameters:
    - texture (Any): The source Metal texture to copy pixel data from.
    - out (NDArray[np.uint8], optional): Reusable writable C-contiguous array matching the texture dimensions.

    Returns:
    - NDArray[np.uint8]: The supplied out array, or a newly allocated writable image of shape (height, width, 4).
    """
    shape = (texture.height(), texture.width(), 4)
    if out is None:
        out = np.empty(shape, dtype=np.uint8)
    elif out.dtype != np.uint8 or out.shape != shape:
        raise ValueError("Output must have dtype uint8 and shape (texture.height(), texture.width(), 4)")
    copy_mtl_texture_to_buffer(texture, memoryview(out))
    return out

from typing import Any

import numpy as np

from syphon.utils.raw import copy_mtl_texture_to_bytes, copy_bytes_to_mtl_texture


def copy_image_to_mtl_texture(image: np.ndarray, texture: Any):
    assert len(image.shape) == 3, "Image has to be of shape (m,n,4)"
    assert image.shape[2] == 4, "Image has to be of shape (m,n,4)"

    data = image.tobytes()
    copy_bytes_to_mtl_texture(data, texture)


def copy_mtl_texture_to_image(texture: Any) -> np.ndarray:
    # todo: support buffer re-use
    data = copy_mtl_texture_to_bytes(texture)
    image = np.frombuffer(data, dtype=np.uint8)
    return image.reshape((texture.height(), texture.width(), 4))

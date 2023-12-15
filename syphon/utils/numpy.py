from typing import Any

import numpy as np

from syphon.utils.raw import mtl_texture_to_bytes


def mtl_texture_to_image(texture: Any) -> np.ndarray:
    data = mtl_texture_to_bytes(texture)
    image = np.frombuffer(data, dtype=np.uint8)
    return image.reshape((texture.height(), texture.width(), 4))

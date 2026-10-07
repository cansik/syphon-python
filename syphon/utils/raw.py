from typing import Any, Optional, TypeVar

import Metal

_WritableBuffer = TypeVar("_WritableBuffer", bytearray, memoryview)


def _byte_view(buffer: Any, *, writable: bool = False) -> memoryview:
    view = memoryview(buffer)
    if not view.c_contiguous:
        raise ValueError("Buffer must be C-contiguous")
    if writable and view.readonly:
        raise ValueError("Output buffer must be writable")
    return view.cast("B")


def _read_layout(texture: Any) -> tuple[int, int, int, int]:
    if texture.pixelFormat() not in (Metal.MTLPixelFormatBGRA8Unorm, Metal.MTLPixelFormatRGBA8Unorm):
        raise Exception("Not correct pixel format (expected MTLPixelFormatBGRA8Unorm or MTLPixelFormatRGBA8Unorm)")
    width, height = texture.width(), texture.height()
    return width, height, width * 4, width * height * 4


def create_mtl_texture(device: Any, width: int, height: int, pixel_format: int = Metal.MTLPixelFormatRGBA8Unorm) -> Any:
    """
    Create a Metal texture with the specified parameters.

    Parameters:
    - device (Any): The Metal device.
    - width (int): The width of the texture.
    - height (int): The height of the texture.
    - pixel_format (int): The pixel format of the texture (default: MTLPixelFormatRGBA8Unorm).

    Returns:
    - Any: The created Metal texture.
    """
    texture_descriptor = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
        pixel_format, width, height, False
    )

    return device.newTextureWithDescriptor_(texture_descriptor)


def copy_bytes_to_mtl_texture(data: bytes | bytearray | memoryview, texture: Any) -> None:
    """
    Copy packed four-byte pixels from a contiguous buffer to a Metal texture.

    Parameters:
    - data (bytes | bytearray | memoryview): Contiguous pixel data; channel order follows the texture format.
    - texture (Any): The target Metal texture to copy the pixel data into.
    """
    width, height = texture.width(), texture.height()
    view = _byte_view(data)
    expected = width * height * 4
    if view.nbytes < expected:
        raise ValueError(f"Buffer is too small (expected at least: {expected}, actual: {view.nbytes})")
    region = Metal.MTLRegionMake2D(0, 0, width, height)
    bytes_per_row = width * 4

    texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
        region,
        0,  # mipmapLevel
        view,
        bytes_per_row,
    )


def copy_mtl_texture_to_buffer(texture: Any, buffer: _WritableBuffer) -> _WritableBuffer:
    """Read RGBA8/BGRA8 pixels into a writable contiguous buffer and return it.

    Supply exactly width * height * 4 bytes. Finish GPU writes before reading;
    this helper does not synchronize the GPU or convert channel order.
    """
    width, height, row, size = _read_layout(texture)
    view = _byte_view(buffer, writable=True)
    if view.nbytes != size:
        raise ValueError(f"Incorrect buffer size (expected: {size}, actual: {view.nbytes})")
    texture.getBytes_bytesPerRow_bytesPerImage_fromRegion_mipmapLevel_slice_(
        view, row, size, Metal.MTLRegionMake2D(0, 0, width, height), 0, 0
    )
    return buffer


def copy_mtl_texture_to_bytes(texture: Any, buffer: Optional[Any] = None) -> bytes:
    """
    Copy pixel data from a Metal texture to a bytes object.

    Parameters:
    - texture (Any): The source Metal texture to copy pixel data from.
    - buffer (Optional[Any]): Writable staging buffer. If None, a new buffer is created.

    Returns:
    - bytes: An independent immutable copy. Use copy_mtl_texture_to_buffer() to reuse storage without this copy.

    Raises:
    - Exception: If the pixel format of the texture is not MTLPixelFormatBGRA8Unorm or MTLPixelFormatRGBA8Unorm.
    - Exception: If the provided buffer is not big enough.
    """
    _, _, _, bytes_per_image = _read_layout(texture)
    if buffer is None:
        buffer = bytearray(bytes_per_image)

    if len(buffer) != bytes_per_image:
        raise Exception(f"Buffer is not big enough (expected: {bytes_per_image}, actual: {len(buffer)})")

    copy_mtl_texture_to_buffer(texture, memoryview(buffer))
    return bytes(_byte_view(buffer))

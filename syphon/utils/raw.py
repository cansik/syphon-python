import ctypes
from typing import Any, Optional

import Metal


def create_mtl_texture(device: Any,
                       width: int,
                       height: int,
                       pixel_format: int = Metal.MTLPixelFormatRGBA8Unorm) -> Any:
    texture_descriptor = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
        pixel_format, width, height, False
    )

    return device.newTextureWithDescriptor_(texture_descriptor)


def copy_bytes_to_mtl_texture(data: bytes, texture: Any):
    region = Metal.MTLRegion((0, 0, 0), (texture.width(), texture.height(), 1))
    bytes_per_row = texture.width() * 4

    texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
        region,
        0,  # mipmapLevel
        data,
        bytes_per_row
    )


def copy_mtl_texture_to_bytes(texture: Any, buffer: Optional[Any] = None) -> bytes:
    if (texture.pixelFormat() != Metal.MTLPixelFormatBGRA8Unorm
            and texture.pixelFormat() != Metal.MTLPixelFormatRGBA8Unorm):
        raise Exception("Not correct pixel format (expected MTLPixelFormatBGRA8Unorm or MTLPixelFormatRGBA8Unorm)")

    bytes_per_row = texture.width() * 4
    bytes_per_image = bytes_per_row * texture.height()
    mipmap_level = 0
    slice_number = 0
    region = Metal.MTLRegionMake2D(0, 0, texture.width(), texture.height())

    if buffer is None:
        buffer = ctypes.create_string_buffer(bytes_per_image)

    if len(buffer) != bytes_per_image:
        raise Exception(f"Buffer is not big enough (expected: {bytes_per_image}, actual: {len(buffer)})")

    texture.getBytes_bytesPerRow_bytesPerImage_fromRegion_mipmapLevel_slice_(buffer,
                                                                             bytes_per_row,
                                                                             bytes_per_image,
                                                                             region,
                                                                             mipmap_level,
                                                                             slice_number)

    raw_bytes = bytes(buffer.raw)
    return raw_bytes

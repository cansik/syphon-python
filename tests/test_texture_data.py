"""Check pixel layout and validation independently of GPU availability."""

import ctypes

import Metal
import pytest

from syphon.utils.raw import copy_bytes_to_mtl_texture, copy_mtl_texture_to_bytes


class MemoryTexture:
    def __init__(self, width=3, height=2, pixel_format=Metal.MTLPixelFormatRGBA8Unorm):
        self._width = width
        self._height = height
        self._format = pixel_format
        self.data = bytes(range(width * height * 4))

    def width(self):
        return self._width

    def height(self):
        return self._height

    def pixelFormat(self):
        return self._format

    def replaceRegion_mipmapLevel_withBytes_bytesPerRow_(self, region, level, data, row_size):
        assert tuple(region.size) == (self._width, self._height, 1)
        assert level == 0
        assert row_size == self._width * 4
        self.data = bytes(data)

    def getBytes_bytesPerRow_bytesPerImage_fromRegion_mipmapLevel_slice_(
        self, buffer, row_size, image_size, region, level, slice_number
    ):
        assert row_size == self._width * 4
        assert image_size == row_size * self._height
        assert tuple(region.size) == (self._width, self._height, 1)
        assert (level, slice_number) == (0, 0)
        ctypes.memmove(buffer, self.data, len(self.data))


@pytest.mark.parametrize("pixel_format", [Metal.MTLPixelFormatRGBA8Unorm, Metal.MTLPixelFormatBGRA8Unorm])
def test_raw_pixels_and_reusable_buffer(pixel_format):
    texture = MemoryTexture(pixel_format=pixel_format)
    data = bytes(reversed(range(24)))
    copy_bytes_to_mtl_texture(data, texture)
    assert copy_mtl_texture_to_bytes(texture) == data
    buffer = ctypes.create_string_buffer(24)
    assert copy_mtl_texture_to_bytes(texture, buffer) == data
    assert buffer.raw == data


def test_unsupported_pixel_format():
    with pytest.raises(Exception, match="pixel format"):
        copy_mtl_texture_to_bytes(MemoryTexture(pixel_format=Metal.MTLPixelFormatR8Unorm))


@pytest.mark.parametrize("size", [0, 23, 25])
def test_wrong_buffer_size(size):
    with pytest.raises(Exception, match="expected: 24"):
        copy_mtl_texture_to_bytes(MemoryTexture(), ctypes.create_string_buffer(size))


def test_numpy_roundtrip_handles_noncontiguous_arrays():
    np = pytest.importorskip("numpy")
    from syphon.utils.numpy import copy_image_to_mtl_texture, copy_mtl_texture_to_image

    image = np.arange(48, dtype=np.uint8).reshape(2, 6, 4)[:, ::2, :]
    assert not image.flags.c_contiguous
    texture = MemoryTexture()
    copy_image_to_mtl_texture(image, texture)
    result = copy_mtl_texture_to_image(texture)
    assert result.shape == (2, 3, 4)
    assert result.dtype == np.uint8
    np.testing.assert_array_equal(result, image)


@pytest.mark.parametrize("shape", [(2, 3), (2, 3, 3), (2, 3, 4, 1)])
def test_numpy_rejects_invalid_image_shape(shape):
    np = pytest.importorskip("numpy")
    from syphon.utils.numpy import copy_image_to_mtl_texture

    with pytest.raises(AssertionError, match="shape"):
        copy_image_to_mtl_texture(np.zeros(shape, dtype=np.uint8), MemoryTexture())

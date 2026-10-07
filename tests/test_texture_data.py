"""Check pixel layout and validation independently of GPU availability."""

import ctypes

import Metal
import pytest

from syphon.utils.raw import copy_bytes_to_mtl_texture, copy_mtl_texture_to_buffer, copy_mtl_texture_to_bytes


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
        self.data = bytes(memoryview(data).cast("B")[: self._width * self._height * 4])

    def getBytes_bytesPerRow_bytesPerImage_fromRegion_mipmapLevel_slice_(
        self, buffer, row_size, image_size, region, level, slice_number
    ):
        assert row_size == self._width * 4
        assert image_size == row_size * self._height
        assert tuple(region.size) == (self._width, self._height, 1)
        assert (level, slice_number) == (0, 0)
        memoryview(buffer).cast("B")[:] = self.data


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
    with pytest.raises(Exception, match="pixel format") as error:
        copy_mtl_texture_to_bytes(MemoryTexture(pixel_format=Metal.MTLPixelFormatR8Unorm))
    assert type(error.value) is Exception


@pytest.mark.parametrize("size", [0, 23, 25])
def test_wrong_buffer_size(size):
    with pytest.raises(Exception, match="expected: 24") as error:
        copy_mtl_texture_to_bytes(MemoryTexture(), ctypes.create_string_buffer(size))
    assert type(error.value) is Exception


@pytest.mark.parametrize("size", [0, 4, 23])
def test_undersized_upload_fails_before_native_call(size):
    texture = MemoryTexture()
    original = texture.data
    with pytest.raises(ValueError, match="at least: 24"):
        copy_bytes_to_mtl_texture(bytes(size), texture)
    assert texture.data is original


@pytest.mark.parametrize("pixel_format", [Metal.MTLPixelFormatRGBA8Unorm_sRGB, Metal.MTLPixelFormatRGBA8Uint])
def test_upload_preserves_raw_format_and_oversized_buffer_support(pixel_format):
    texture = MemoryTexture(pixel_format=pixel_format)
    data = bytes(range(32))
    copy_bytes_to_mtl_texture(data, texture)
    assert texture.data == data[:24]


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


def test_buffer_read_reuses_storage_and_bytes_result_is_independent():
    texture = MemoryTexture()
    out = bytearray(24)
    assert copy_mtl_texture_to_buffer(texture, out) is out
    assert out == texture.data
    snapshot = copy_mtl_texture_to_bytes(texture, out)
    out[0] = 255
    assert snapshot == texture.data


@pytest.mark.parametrize("writable", [False, True])
def test_noncontiguous_buffer_is_rejected(writable):
    buffer = memoryview(bytearray(48))[::2]
    with pytest.raises(ValueError, match="C-contiguous"):
        if writable:
            copy_mtl_texture_to_buffer(MemoryTexture(), buffer)
        else:
            copy_bytes_to_mtl_texture(buffer, MemoryTexture())


def test_readonly_output_is_rejected():
    with pytest.raises(ValueError, match="writable"):
        copy_mtl_texture_to_buffer(MemoryTexture(), bytes(24))


def test_numpy_upload_borrows_contiguous_array_storage():
    np = pytest.importorskip("numpy")
    from syphon.utils.numpy import copy_image_to_mtl_texture

    texture = MemoryTexture()
    captured = []
    texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_ = lambda region, level, data, row: captured.append(data)
    image = np.arange(24, dtype=np.uint8).reshape(2, 3, 4)
    copy_image_to_mtl_texture(image, texture)
    assert captured[0].obj is image


@pytest.mark.parametrize("kind", ["masked", "datetime", "uint16"])
def test_numpy_preserves_existing_serialization_for_other_arrays(kind):
    np = pytest.importorskip("numpy")
    from syphon.utils.numpy import copy_image_to_mtl_texture

    image = np.arange(24, dtype=np.uint8).reshape(2, 3, 4)
    if kind == "masked":
        image = np.ma.array(image, mask=False, fill_value=17)
        image.mask[0, 0, 0] = True
    elif kind == "datetime":
        image = image.astype("datetime64[ns]")
    else:
        image = image.astype(np.uint16)
    texture = MemoryTexture()
    copy_image_to_mtl_texture(image, texture)
    assert texture.data == image.tobytes()[:24]


def test_numpy_read_reuses_output_and_default_is_writable():
    np = pytest.importorskip("numpy")
    from syphon.utils.numpy import copy_mtl_texture_to_image

    texture = MemoryTexture()
    out = np.empty((2, 3, 4), dtype=np.uint8)
    assert copy_mtl_texture_to_image(texture, out=out) is out
    np.testing.assert_array_equal(out.reshape(-1), np.arange(24))
    result = copy_mtl_texture_to_image(texture)
    assert result.flags.writeable
    texture.data = bytes(reversed(range(24)))
    copy_mtl_texture_to_image(texture, out=out)
    assert out.tobytes() == texture.data
    assert result.tobytes() != out.tobytes()


@pytest.mark.parametrize("kind", ["shape", "dtype", "strided", "readonly"])
def test_numpy_rejects_invalid_output(kind):
    np = pytest.importorskip("numpy")
    from syphon.utils.numpy import copy_mtl_texture_to_image

    out = np.empty((2, 3, 4), dtype=np.uint8)
    if kind == "shape":
        out = out[:1]
    elif kind == "dtype":
        out = out.astype(np.float32)
    elif kind == "strided":
        out = np.empty((2, 6, 4), dtype=np.uint8)[:, ::2]
    else:
        out.flags.writeable = False
    with pytest.raises(ValueError):
        copy_mtl_texture_to_image(MemoryTexture(), out=out)

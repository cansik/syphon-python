"""Measure the installed library; save and compare runs from different revisions.

Run from a development checkout with the NumPy extra. Results are local development
artifacts, not timing assertions. Host measurements isolate Python buffer handling;
Metal measurements include real texture transfers. No historical implementations are
embedded, so this script can also run against an earlier installation of the library.
"""

import argparse
import gc
import inspect
import json
import math
import platform
import statistics
import time
import tracemalloc
from importlib.metadata import version
from pathlib import Path

import Metal
import numpy as np
import objc

import syphon
from syphon.utils import numpy as image_utils, raw


class HostTexture:
    """CPU storage implementing the texture transfer interface, without a GPU."""

    def __init__(self, width: int, height: int):
        self._width, self._height = width, height
        self.pixels = bytearray(width * height * 4)

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def pixelFormat(self) -> int:
        return Metal.MTLPixelFormatRGBA8Unorm

    def replaceRegion_mipmapLevel_withBytes_bytesPerRow_(self, region, level, data, row):
        memoryview(self.pixels)[:] = memoryview(data).cast("B")[: len(self.pixels)]

    def getBytes_bytesPerRow_bytesPerImage_fromRegion_mipmapLevel_slice_(self, buffer, *args):
        memoryview(buffer).cast("B")[:] = self.pixels


def measure(name, operation, *, iterations, repeats, finish=None) -> dict:
    def batch(count):
        with objc.autorelease_pool():
            started = time.perf_counter_ns()
            for _ in range(count):
                operation()
            elapsed = (time.perf_counter_ns() - started) / count / 1_000_000
            if finish is not None:
                finish()  # GPU completion is outside CPU submission timing.
        return elapsed

    batch(min(3, iterations))
    samples = [batch(iterations) for _ in range(repeats)]
    gc.collect()
    with objc.autorelease_pool():
        tracemalloc.start()
        try:
            result = operation()
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
            if finish is not None:
                finish()
        del result
    return {
        "name": name,
        "iterations": iterations,
        "repeats": repeats,
        "ms": statistics.median(samples),
        "peak_mib": peak / (1024 * 1024),
        "samples_ms": samples,
    }


def transfer_cases(label, texture, image, settings, skipped) -> list[dict]:
    image_utils.copy_image_to_mtl_texture(image, texture)
    np.testing.assert_array_equal(image_utils.copy_mtl_texture_to_image(texture), image)
    rows = [
        measure(f"{label}/upload", lambda: image_utils.copy_image_to_mtl_texture(image, texture), **settings),
        measure(f"{label}/download", lambda: image_utils.copy_mtl_texture_to_image(texture), **settings),
    ]
    if "out" in inspect.signature(image_utils.copy_mtl_texture_to_image).parameters:
        out = np.empty_like(image)
        assert image_utils.copy_mtl_texture_to_image(texture, out=out) is out
        np.testing.assert_array_equal(out, image)
        rows.append(
            measure(
                f"{label}/download-reuse", lambda: image_utils.copy_mtl_texture_to_image(texture, out=out), **settings
            )
        )
    else:
        skipped.append(f"{label}/download-reuse: installed library has no out parameter")
    return rows


def metal_cases(device, image, settings, skipped) -> list[dict]:
    height, width, _ = image.shape
    texture = raw.create_mtl_texture(device, width, height)
    if texture is None:
        raise RuntimeError("Could not allocate the benchmark texture")
    rows = transfer_cases("metal", texture, image, settings, skipped)
    with syphon.SyphonMetalServer("Transfer benchmark", device=device, is_private=True) as server:
        pending = []

        def publish(*, manual_submit=False, complete=False):
            buffer = server.command_queue.commandBuffer()
            server.publish_frame_texture(texture, command_buffer=buffer, auto_commit=not manual_submit)
            if manual_submit:
                buffer.commit()
            if complete:
                buffer.waitUntilCompleted()
                if buffer.error() is not None:
                    raise RuntimeError(str(buffer.error()))
            else:
                pending.append(buffer)

        def finish():
            for buffer in pending:
                buffer.waitUntilCompleted()
                if buffer.error() is not None:
                    raise RuntimeError(str(buffer.error()))
            pending.clear()

        publish(complete=True)
        output = server.new_frame_image
        if output.storageMode() == Metal.MTLStorageModeManaged:
            buffer = server.command_queue.commandBuffer()
            encoder = buffer.blitCommandEncoder()
            encoder.synchronizeResource_(output)
            encoder.endEncoding()
            buffer.commit()
            buffer.waitUntilCompleted()
        expected = image[:, :, [2, 1, 0, 3]].tobytes()
        assert raw.copy_mtl_texture_to_bytes(output) == expected
        rows.append(measure("metal/publish-complete", lambda: publish(complete=True), **settings))
        rows.append(
            measure("metal/publish-async-submission", lambda: publish(manual_submit=True), finish=finish, **settings)
        )
    return rows


def opengl_cases(width, height, settings, skipped) -> list[dict]:
    try:
        import AppKit
        from OpenGL import GL
    except ImportError:
        skipped.append("opengl: requires the opengl extra")
        return []
    pixel_format = AppKit.NSOpenGLPixelFormat.alloc().initWithAttributes_(
        [AppKit.NSOpenGLPFAOpenGLProfile, AppKit.NSOpenGLProfileVersion3_2Core, AppKit.NSOpenGLPFAColorSize, 24, 0]
    )
    context = (
        None
        if pixel_format is None
        else AppKit.NSOpenGLContext.alloc().initWithFormat_shareContext_(pixel_format, None)
    )
    if context is None:
        skipped.append("opengl: no usable context")
        return []
    previous = AppKit.NSOpenGLContext.currentContext()
    context.makeCurrentContext()
    texture = GL.glGenTextures(1)
    try:
        pixels = np.empty((height, width, 4), dtype=np.uint8)
        pixels[:] = (17, 53, 199, 255)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, width, height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, pixels)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glFinish()
        with syphon.SyphonOpenGLServer("OpenGL benchmark", is_private=True) as server:
            return [
                measure(
                    "opengl/publish-queried-size",
                    lambda: server.publish_frame_texture(texture),
                    finish=GL.glFinish,
                    **settings,
                ),
                measure(
                    "opengl/publish-known-size",
                    lambda: server.publish_frame_texture(texture, size=(width, height)),
                    finish=GL.glFinish,
                    **settings,
                ),
            ]
    finally:
        GL.glDeleteTextures([texture])
        if previous is None:
            AppKit.NSOpenGLContext.clearCurrentContext()
        else:
            previous.makeCurrentContext()


def discovery_cases(skipped) -> list[dict]:
    with syphon.SyphonServerDirectory() as directory:
        rows = [measure("discovery/servers", lambda: directory.servers, iterations=2, repeats=3)]
        if hasattr(type(directory), "server_snapshot"):
            rows.append(measure("discovery/snapshot", lambda: directory.server_snapshot, iterations=30, repeats=7))
        else:
            skipped.append("discovery/snapshot: installed library has no server_snapshot")
    return rows


def positive_int(value: str) -> int:
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return result


def compare_reports(current: dict, previous: dict) -> tuple[list[dict], list[str]]:
    if previous["schema_version"] != 1:
        raise ValueError("Unsupported benchmark report schema")
    if (current["width"], current["height"]) != (previous["width"], previous["height"]):
        raise ValueError("Cannot compare runs with different image dimensions")
    if not isinstance(previous["environment"], dict) or not isinstance(previous["results"], list):
        raise ValueError("Invalid benchmark report")
    baseline = {row["name"]: row for row in previous["results"]}
    if len(baseline) != len(previous["results"]):
        raise ValueError("Duplicate benchmark case names")
    for row in baseline.values():
        if not isinstance(row["ms"], (int, float)) or not math.isfinite(row["ms"]) or row["ms"] <= 0:
            raise ValueError("Previous timings must be finite positive numbers")
        if not isinstance(row["peak_mib"], (int, float)) or not math.isfinite(row["peak_mib"]) or row["peak_mib"] < 0:
            raise ValueError("Previous allocation peaks must be finite nonnegative numbers")
    warnings = [
        f"Environment differs: {key} ({previous['environment'].get(key)!r} -> {value!r})"
        for key, value in current["environment"].items()
        if previous["environment"].get(key) != value
    ]
    comparisons = []
    for row in current["results"]:
        before = baseline.get(row["name"])
        comparisons.append(
            {
                "name": row["name"],
                "previous_ms": None if before is None else before["ms"],
                "current_ms": row["ms"],
                "previous_peak_mib": None if before is None else before["peak_mib"],
                "current_peak_mib": row["peak_mib"],
                "speedup": None if before is None else before["ms"] / row["ms"],
            }
        )
    return comparisons, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=positive_int, default=3840)
    parser.add_argument("--height", type=positive_int, default=2160)
    parser.add_argument("--iterations", type=positive_int, default=30)
    parser.add_argument("--repeats", type=positive_int, default=7)
    parser.add_argument("--backend", choices=("host", "metal", "all"), default="all")
    parser.add_argument("--opengl", action="store_true")
    parser.add_argument("--discovery", action="store_true", help="Include the default discovery wait (several seconds)")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", type=Path, help="Compare with a locally saved run")
    args = parser.parse_args(argv)
    previous = None
    if args.compare is not None:
        try:
            previous = json.loads(args.compare.read_text())
            compare_reports({"width": args.width, "height": args.height, "environment": {}, "results": []}, previous)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(str(error))
    image = np.arange(args.width * args.height * 4, dtype=np.uint8).reshape(args.height, args.width, 4)
    settings = {"iterations": args.iterations, "repeats": args.repeats}
    rows, skipped = [], []
    device = None
    with objc.autorelease_pool():
        if args.backend in ("host", "all"):
            rows.extend(transfer_cases("host", HostTexture(args.width, args.height), image, settings, skipped))
        if args.backend in ("metal", "all"):
            device = Metal.MTLCreateSystemDefaultDevice()
            if device is None:
                skipped.append("metal: no device available")
            else:
                rows.extend(metal_cases(device, image, settings, skipped))
        if args.opengl:
            rows.extend(opengl_cases(args.width, args.height, settings, skipped))
        if args.discovery:
            rows.extend(discovery_cases(skipped))
        report = {
            "schema_version": 1,
            "library_version": version("syphon-python"),
            "environment": {
                "macos": platform.mac_ver()[0],
                "architecture": platform.machine(),
                "python": platform.python_version(),
                "numpy": np.__version__,
                "device": None if device is None else str(device.name()),
            },
            "width": args.width,
            "height": args.height,
            "results": rows,
            "skipped": skipped,
        }
    print(f"{'Operation':38} {'ms':>10} {'peak MiB':>10}")
    for row in rows:
        print(f"{row['name']:38} {row['ms']:10.3f} {row['peak_mib']:10.3f}")
    for reason in skipped:
        print(f"Skipped: {reason}")
    if previous is not None:
        comparisons, warnings = compare_reports(report, previous)
        report["comparison"], report["comparison_warnings"] = comparisons, warnings
        print("\nCompared with saved run:")
        for row in comparisons:
            print(f"{row['name']}: " + ("new case" if row["speedup"] is None else f"{row['speedup']:.2f}x"))
        for warning in warnings:
            print(f"Warning: {warning}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    return 1 if args.backend == "metal" and device is None else 0


if __name__ == "__main__":
    raise SystemExit(main())

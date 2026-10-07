"""Headless examples must answer discovery requests from clients started later."""

import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.metal
@pytest.mark.parametrize(
    "example", ["MetalServerExample.py", "MetalServerExampleMini.py", "MetalServerAsyncExample.py"]
)
def test_late_client_discovers_running_metal_example(example, tmp_path):
    import Metal

    if Metal.MTLCreateSystemDefaultDevice() is None:
        pytest.skip("A Metal device is required")
    if example.endswith("Mini.py"):
        pytest.importorskip("numpy")
    ready = tmp_path / "server-uuid"
    publisher = textwrap.dedent("""
        import runpy
        import sys
        from pathlib import Path
        import syphon

        class ObservedServer(syphon.SyphonMetalServer):
            announced = False

            def publish_frame_texture(self, *args, **kwargs):
                super().publish_frame_texture(*args, **kwargs)
                if not self.announced:
                    self.announced = True
                    Path(sys.argv[2]).write_text(self.server_description.uuid)

        syphon.SyphonMetalServer = ObservedServer
        runpy.run_path(sys.argv[1], run_name="__main__")
    """)
    receiver = textwrap.dedent("""
        import sys
        import time
        import syphon

        with syphon.SyphonServerDirectory() as directory:
            directory.run_loop_interval = 0.01
            deadline = time.monotonic() + 5
            description = None
            while time.monotonic() < deadline:
                description = next((s for s in directory.servers if s.uuid == sys.argv[1]), None)
                if description is not None:
                    break
            assert description is not None, "Late client could not discover the example server"
            with syphon.SyphonMetalClient(description) as client:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    directory.update_run_loop()
                    if client.has_new_frame:
                        image = client.new_frame_image
                        if image is not None:
                            assert image.width() > 0 and image.height() > 0
                            break
                else:
                    raise AssertionError("Discovered server delivered no Metal texture")
    """)
    with (tmp_path / "publisher.log").open("w+") as output:
        process = subprocess.Popen(
            [sys.executable, "-c", publisher, str(ROOT / "examples" / example), str(ready)],
            stdout=output,
            stderr=output,
        )
        try:
            deadline = time.monotonic() + 10
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            assert ready.exists(), "Example did not begin publishing"
            # Import Syphon only now, in a fresh process: its initial announcement has passed.
            result = subprocess.run(
                [sys.executable, "-c", receiver, ready.read_text()],
                capture_output=True,
                text=True,
                timeout=15,
            )
            assert result.returncode == 0, result.stdout + result.stderr
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        output.seek(0)
        assert process.returncode == 0, output.read()

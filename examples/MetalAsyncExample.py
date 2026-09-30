"""Wait for Syphon frames with asyncio; texture retrieval remains explicit."""

import asyncio
from contextlib import suppress

import syphon


async def main():
    with syphon.SyphonServerDirectory() as directory:
        directory.run_loop_interval = 0.001

        async def pump_discovery():
            while True:
                directory.update_run_loop()
                await asyncio.sleep(0.01)

        pump = asyncio.create_task(pump_discovery())
        try:
            print("Waiting for a Syphon server; press Ctrl+C to stop.")
            while not (servers := directory.servers):
                await asyncio.sleep(0.05)
            with syphon.SyphonMetalClient(servers[0]) as client:
                while client.is_valid:
                    try:
                        await client.wait_for_frame(timeout=5)
                    except asyncio.TimeoutError:
                        print("No new frame in five seconds")
                        continue
                    except ConnectionError:
                        break
                    frame = client.new_frame_image
                    if frame is not None:
                        print(f"Frame: {frame.width()} x {frame.height()}")
                        del frame
        finally:
            pump.cancel()
            with suppress(asyncio.CancelledError):
                await pump


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

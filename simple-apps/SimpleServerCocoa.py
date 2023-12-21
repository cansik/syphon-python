from typing import Any, Optional, Callable

import Metal
from Cocoa import NSObject, NSApplication, NSApp, NSWindow
from MetalKit import MTKView
from PyObjCTools import AppHelper

import syphon


class SimpleMTKViewDelegate(NSObject):

    def init(self):
        super().init()
        self.command_queue: Optional[Any] = None
        self.on_draw_callback: Optional[Callable[[SimpleMTKViewDelegate, MTKView, Any], None]] = None
        return self

    def mtkView_drawableSizeWillChange_(self, view, size):
        pass

    def drawInMTKView_(self, view):
        if self.command_queue is None:
            self.command_queue = view.device().newCommandQueue()

        onscreen_descriptor = view.currentRenderPassDescriptor()

        if onscreen_descriptor is None:
            return

        command_buffer = self.command_queue.commandBuffer()
        onscreen_command_encoder = command_buffer.renderCommandEncoderWithDescriptor_(onscreen_descriptor)

        if onscreen_command_encoder is None:
            return

        try:
            if self.on_draw_callback is not None:
                self.on_draw_callback(self, view, command_buffer)

            # Set render state and resources.
            # ...

            # Issue draw calls.
            # ...

            onscreen_command_encoder.endEncoding()

            # Register the drawable's presentation.
            current_drawable = view.currentDrawable()
            if current_drawable:
                command_buffer.presentDrawable_(current_drawable)

        except Exception as e:
            print(f"Error in rendering: {e}")
        finally:
            # Finalize your onscreen CPU work and commit the command buffer to the GPU.
            command_buffer.commit()


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        pass

    def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
        # Terminate the application when the last window is closed
        return True


class App:
    def __init__(self):
        self.red = 0

        self.app = NSApplication.sharedApplication()

        # we must keep a reference to the delegate object ourselves,
        # NSApp.setDelegate_() doesn't retain it. A local variable is
        # enough here.
        self.delegate = AppDelegate.alloc().init()
        NSApp().setDelegate_(self.delegate)

        self.window = NSWindow.alloc()
        frame = ((500.0, 500.0), (640.0, 480.0))
        self.window.initWithContentRect_styleMask_backing_defer_(frame, 15, 2, 0)
        self.window.setTitle_("Simple Server")
        self.window.setLevel_(3)  # floating window

        # Add the MTKView as a subview to the window
        view = self.window.contentView()

        # create mtl view
        device = Metal.MTLCreateSystemDefaultDevice()
        self.metal_view = MTKView.alloc().initWithFrame_(view.bounds())
        self.metal_view.setDevice_(device)
        self.metal_view.setClearColor_(Metal.MTLClearColorMake(1.0, 1.0, 0.6, 1.0))
        view.addSubview_(self.metal_view)

        # add mtl delegate (store it in self to not get gc'd)
        self.mtk_delegate: SimpleMTKViewDelegate = SimpleMTKViewDelegate.alloc().init()
        self.metal_view.setDelegate_(self.mtk_delegate)

        # add callback
        self.mtk_delegate.on_draw_callback = self.on_draw

        self.syphon_server = syphon.SyphonMetalServer("Cocoa")

    def run(self):
        self.window.display()
        self.window.orderFrontRegardless()

        AppHelper.runEventLoop()

    def on_draw(self, delegate, view, command_buffer):
        self.red = (self.red + 1) % 256
        self.metal_view.setClearColor_(Metal.MTLClearColorMake(self.red / 255, 0.8, (255 - self.red) / 255, 1.0))

        texture = view.currentDrawable().texture()
        self.syphon_server.publish_frame_texture(texture)

    def stop(self):
        self.syphon_server.stop()


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()

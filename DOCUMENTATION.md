# Documentation
The syphon-python library is a wrapper for the [Syphon framework](https://github.com/Syphon/Syphon-Framework) for the Python language. It exposes the Objective-C API to the Python world and adds helper methods to easily interoperate with Syphon. Syphon is an open source Mac OS X technology that allows applications to share video and still images with each other in real time.

## Why a new library?
There are already wrappers like [syphonpy](https://github.com/njazz/syphonpy) that do the same thing as syphon-python. There are two main reasons why syphon-python was implemented:

### Modern Graphics Pipeline
Most existing Python wrappers for Syphon only support the OpenGL framework. Even though OpenGL is still available in modern MacOS versions, as of **MacOS Mojave 10.14**, the framework is marked as deprecated and should be avoided. And while many applications are switching to the Metal graphics backend, Syphon needs to do the same.

The Syphon framework already supports the Metal graphics backend, but the wrappers usually do not. Syphon-python adds support for Metal and retains OpenGL.

### Objective-C to Python
To add support for the new Metal graphics backend, the existing wrappers could be extended. However, many of them use an intermediate wrapper in C to expose the Objective-C API to Python. For Python developers it can be difficult to extend existing C code, so syphon-python uses [PyObjC](https://pyobjc.readthedocs.io/en/latest/), a Python to Objective-C bridge.

## Syphon Package
The main package of syphon-python is called `syphon` and contains all the necessary objects and classes of the library. To use syphon-python in a project, start with the following import statement.

```python
import syphon
```

For each Metal class there is also an OpenGL counterpart. It is worth noting that Syphon supports interopability between Metal and OpenGL. This means that it is possible to run a Metal-based Syphon server and receive it in an OpenGL client and vice versa.

## Syphon Server
To share graphic textures with other applications, a syphon server (sender) has to be created. All server implementations are based on the `syphon.server.BaseSyphonServer` and share the same interface, except the constructor. The following code example creates either a Metal oder OpenGL based server, using the app name `Demo` and using the default device or context.

```python
# create a Metal based server
server = syphon.SyphonMetalServer("Demo")

# create an OpenGL based server
server = syphon.SyphonOpenGLServer("Demo")
```

To publish a texture, the method `syphon.server.BaseSyphonServer.publish_frame_texture()` can be used. We assume that the corresponding texture has already been created and is available in the `texture` variable. To see how to create and fill a MTLTexture or glTexture, please have a look at the [examples](https://github.com/cansik/syphon-python/tree/main/examples).

```python
texture = ...  # MTLTexture or glTexture
server.publish_frame_texture(texture)
```

The `syphon.server.BaseSyphonServer.publish_frame_texture()` contains a flag called `flip` to flip the texture horizontally. This can be set to `True` if the image is upside down on the receiver side.

It is also possible to check if a server has connected clients with the `has_clients` property.

To clean up and release allocated resources, a server should be stopped with the `syphon.server.BaseSyphonServer.stop()` method.

```python
if not server.has_clients:
    server.stop()
```

### Metal Server
On initialisation, the `syphon.server.SyphonMetalServer` creates a new [system default Metal device](https://developer.apple.com/documentation/metal/1433401-mtlcreatesystemdefaultdevice) as well as a new [command queue](https://developer.apple.com/documentation/metal/mtlcommandqueue). It is possible to override which [MTLDevice](https://developer.apple.com/documentation/metal/mtldevice) the Syphon server is running on or which type of command queue is used. This can be done by using the additional parameters of the `syphon.server.SyphonMetalServer`.

```python
import Metal

# overwrite the mtl_device
mtl_device = Metal.MTLCreateSystemDefaultDevice()
server = syphon.SyphonMetalServer("Demo", device=mtl_device)

# or also create custom command queue
mtl_command_queue = mtl_device.newCommandQueue()
server = syphon.SyphonMetalServer("Demo", device=mtl_device, command_queue=mtl_command_queue)
```

### OpenGL Server
Install `syphon-python[opengl]` to enable OpenGL support. Metal usage does not require this extra.

On initialisation, the `syphon.server.SyphonOpenGLServer` tries to find the current [cglContextObj](https://developer.apple.com/documentation/appkit/nsopenglcontext/1436158-cglcontextobj) using the current [NSOpenGLContext](https://developer.apple.com/documentation/appkit/nsopenglcontext). It is possible to override the automatic lookup by passing a valid `cglContextObj` as a parameter to the `syphon.server.SyphonOpenGLServer`.

```python
import AppKit

ns_ctx = AppKit.NSOpenGLContext.currentContext()
cgl_context = ns_ctx.CGLContextObj()

server = syphon.SyphonOpenGLServer("Demo", cgl_context_obj=cgl_context)
```

For example, if glfw is used to create an OpenGL window, it is enough to set the current context through glfw and the `syphon.server.SyphonOpenGLServer` will be able to find this context on its own.

```python
glfw.make_context_current(window)
server = syphon.SyphonOpenGLServer("Demo")
```

## Shared Directory
To get a list of active Syphon servers on the system, the `syphon.server_directory.SyphonServerDirectory` can be used. The resulting list of objects is of type `syphon.server_directory.SyphonServerDescription`.

```python
directory = syphon.SyphonServerDirectory()
servers = directory.servers

for server in servers:
    print(f"{server.app_name} ({server.uuid})")
```

It is also possible to listen for events when a server changes its status. However, it is important to update the NSRunLoop to receive messages. This can be done by repeatedly calling `directory.update_run_loop()`.

```python
def handler(event):
    print("A new server has been announced.")


directory.add_observer(syphon.SyphonServerNotification.Announce, handler)

while True:
    directory.update_run_loop()
    time.sleep(1.0)
```

## Syphon Client
To receive graphic textures from other applications, a syphon client (receiver) must be created. All client implementations are based on `syphon.client.BaseSyphonClient` and share the same interface except for the constructor. The following code example creates either a Metal or OpenGL based client, using the first found server description and the default device or context.

```python
# receive the first server description
directory = syphon.SyphonServerDirectory()
server_info = directory.servers[0]

# create a Metal client
client = syphon.SyphonMetalClient(server_info)

# create an OpenGL client
client = syphon.SyphonOpenGLClient(server_info)
```

To get textures, it is possible to first check if the server has provided a new texture using the `has_new_frame` property, and then read the new frame image using the `new_frame_image` property.

```python
if client.has_new_frame:
    texture = client.new_frame_image  # either MTLTexture or glTexture
```

To stop the client and disconnect from the server, the `syphon.client.BaseSyphonClient.stop()` method can be used.

```python
client.stop()
```

### Metal Client
As with the [metal server](#metal-server), it is possible to overwrite the device which the metal client is running on. This can be done by using the additional parameters of the `syphon.client.SyphonMetalClient`.

```python
import Metal

# overwrite the mtl_device
mtl_device = Metal.MTLCreateSystemDefaultDevice()
client = syphon.SyphonMetalClient(server_info, device=mtl_device)
```

### OpenGL Client
Install `syphon-python[opengl]` to enable OpenGL support.

As with the [opengl server](#opengl-server), it is possible to override the automatic lookup by passing a valid `cglContextObj` as a parameter to the `syphon.client.SyphonOpenGLClient`.

```python
import AppKit

ns_ctx = AppKit.NSOpenGLContext.currentContext()
cgl_context = ns_ctx.CGLContextObj()

client = syphon.SyphonOpenGLClient(server_info, cgl_context_obj=cgl_context)
```

## Utilities
To make sharing graphic textures as easy as possible, the library provides some utility methods to manipulate texture data.

### Raw
The `syphon.utils.raw` module contains methods to create and manipulate textures with a raw `bytes` array.

#### Create MTLTexture
To create an [MTLTexture](https://developer.apple.com/documentation/metal/mtltexture) the method `syphon.utils.raw.create_mtl_texture` can be used. It is possible to create your own default device or use a server's `syphon.server.SyphonMetalServer.device` property to get the current device.

```python
import Metal
from syphon.utils.raw import create_mtl_texture

mtl_device = Metal.MTLCreateSystemDefaultDevice()
texture = create_mtl_texture(mtl_device, 512, 512)
```

#### Manipulate MTLTexture
To write `bytes` to an [MTLTexture](https://developer.apple.com/documentation/metal/mtltexture) the method `syphon.utils.raw.copy_bytes_to_mtl_texture()` can be used.

```python
from syphon.utils.raw import copy_bytes_to_mtl_texture

data = ...  # bytes() based buffer
texture = ...  # MLTTexture object

copy_bytes_to_mtl_texture(data, texture)
```

To read `bytes` from an [MTLTexture](https://developer.apple.com/documentation/metal/mtltexture) the method `syphon.utils.raw.copy_mtl_texture_to_bytes()` can be used.

```python
from syphon.utils.raw import copy_mtl_texture_to_bytes

texture = ...  # MLTTexture object

data = copy_mtl_texture_to_bytes(texture)  # returns bytes
```

### Numpy
If you are working with [Numpy](https://numpy.org/) arrays, the `syphon.utils.numpy` package contains helper methods for reading and writing numpy images to and from [MTLTexture](https://developer.apple.com/documentation/metal/mtltexture).

It is important to note that the `numpy` package is not installed by default, it must be installed using `pip install 'syphon-python[numpy]'`.

To write a numpy image to a MTLTexture, the `syphon.utils.numpy.copy_image_to_mtl_texture()` method can be used.

```python
import numpy as np
from syphon.utils.numpy import copy_image_to_mtl_texture

texture = ...  # MLTTexture object

# create RGBA image
texture_data = np.zeros((512, 512, 4), dtype=np.uint8)

# copy image to texture
copy_image_to_mtl_texture(texture_data, texture)
```

To read a numpy image from a MTLTexture, the `syphon.utils.numpy.copy_mtl_texture_to_image()` method can be used.

```python
import numpy as np
from syphon.utils.numpy import copy_mtl_texture_to_image

texture = ...  # MLTTexture object

texture_data = copy_mtl_texture_to_image(texture)  # returns numpy array
```

## Python Binding
As described in the [Objective-C to Python](#objective-c-to-python) chapter, the syphon-python library is based on the [PyObjC](https://pyobjc.readthedocs.io/en/latest/) Python to Objective-C bridge. This means that there is no intermediate wrapper between Python and Objective-C, and it is possible to access and call Objective-C objects directly from Python. This can be useful if a method of the original Syphon framework has not yet been exposed by the wrapper.

### Access Objective-C Objects
To access the raw Objective-C object of a `syphon.server.SyphonMetalServer`, it is possible to access the `syphon.server.SyphonMetalServer.context` variable. To get a list of methods that can be called, the `dir()` method can be used.

```python
server = syphon.SyphonMetalServer("Demo")
objc_syphon_metal_server = server.context

print(dir(objc_syphon_metal_server))
```

### Raw Pointers to Python Objective-C Objects
The framework expects PyObjC pointers to be passed to the methods. Sometimes only raw ctype pointers are available. This example shows how to cast a [nanogui](https://github.com/mitsuba-renderer/nanogui) MTLTexture pointer to a PyObjC object.

```python
import ctypes
from typing import Any

import objc
from nanogui import Screen


def get_mtl_texture(texture: Any) -> Any:
    ctypes.pythonapi.PyCapsule_GetName.restype = ctypes.c_char_p
    ctypes.pythonapi.PyCapsule_GetName.argtypes = [ctypes.py_object]
    capsule_name = ctypes.pythonapi.PyCapsule_GetName(texture)
    
    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
    result = ctypes.pythonapi.PyCapsule_GetPointer(texture, capsule_name)

    mtl_texture = objc.objc_object(c_void_p=result)
    return mtl_texture


class SimpleServerScreen(Screen):
    ...

    def send(self):
        texture = self.metal_texture()  # of type PyCapsule
        texture_pointer = get_mtl_texture(texture)
        self.syphon_server.publish_frame_texture(texture_pointer, is_flipped=True)
```


## Frame Notifications

When receiving frames, an application can check `has_new_frame` in its rendering loop. If the application does not already have such a loop, a callback can be used to notify it when a frame arrives. Both Metal and OpenGL clients accept a `new_frame_handler` which receives the client as its argument.

The following example uses a Python event to signal the application that a new frame is available.

```python
import threading

available = threading.Event()

with syphon.SyphonMetalClient(description, new_frame_handler=lambda client: available.set()) as client:
    # wait for a notification, then retrieve the latest texture
    if available.wait(timeout=5):
        available.clear()
        texture = client.new_frame_image
```

Syphon calls the handler on a background thread. Keep the handler short and perform UI or OpenGL work on the application thread. A client must also be stopped outside this callback to avoid blocking Syphon's own notification thread.

For applications using asyncio, `callback_loop=asyncio.get_running_loop()` can be passed to deliver the handler on that event loop instead. The handler is still a regular Python function; it can use `asyncio.create_task()` to start asynchronous work.

### Waiting with Asyncio

If an application already uses asyncio, `wait_for_frame()` allows it to wait for an image while other tasks continue running. The method waits for availability; the image is then retrieved separately through `new_frame_image`.

```python
async def receive_frame(description):
    with syphon.SyphonMetalClient(description) as client:
        # wait up to five seconds for a frame
        await client.wait_for_frame(timeout=5)
        texture = client.new_frame_image
        return texture
```

A timeout raises `asyncio.TimeoutError`, and a disconnected server raises `ConnectionError`. Syphon provides the latest frame, so a slow receiver may skip intermediate frames. Waiting does not create a queue of images.

For complete examples, see [MetalCallbackExample](https://github.com/cansik/syphon-python/blob/main/examples/MetalCallbackExample.py) and [MetalAsyncExample](https://github.com/cansik/syphon-python/blob/main/examples/MetalAsyncExample.py). The asyncio example also shows how to process Cocoa events for server discovery without a UI.

## Private Servers

By default, Syphon servers appear in the shared directory so that other applications can find them. If an output is only intended for a specific client, `is_private=True` can be used to hide it from discovery. The client then connects using the server's description directly.

```python
with syphon.SyphonMetalServer("Internal", is_private=True) as server:
    # connect directly without searching the shared directory
    with syphon.SyphonMetalClient(server.server_description, server.device) as client:
        ...
```

This works for both Metal and OpenGL servers. A private server is hidden, but is not protected by authentication. When passing its description to another process, preserve the complete `server_description.raw` dictionary. It can be converted back using `SyphonServerDescription.from_native(raw)`.

### Changing the Server Name

An application may want to rename an output when its content changes, for example when switching from a camera feed to a preview. Assigning `server.name` updates the running server and its name in discovery.

```python
server.name = "Camera Preview"
```

### Accessing the Server Output

To preview a server's output in the same application, `server.new_frame_image` can be used without creating an additional client. It returns a Metal texture or an OpenGL image, depending on the server.

```python
# retrieve the current output after publishing a frame
image = server.new_frame_image
if image is not None:
    ...  # display or inspect the image
```

The result may be `None` before the first frame is published. Keep the image alive while using it and release Python references when finished; PyObjC handles native memory management. The image represents the current output rather than a saved copy of an earlier frame.

See [PrivateMetalExample](https://github.com/cansik/syphon-python/blob/main/examples/PrivateMetalExample.py) for a complete example of private connections, renaming, and output access.

## Direct OpenGL Rendering

If an application already renders with OpenGL, it can draw directly into Syphon's framebuffer instead of creating a separate texture to publish. `bind_to_draw_frame()` selects that framebuffer, and `unbind_and_publish()` publishes the result after drawing.

The following example assumes an OpenGL context is already current.

```python
with syphon.SyphonOpenGLServer("Direct output", depth_buffer_resolution=24) as server:
    if server.bind_to_draw_frame((640, 480)):
        try:
            ...  # draw the scene using OpenGL
        finally:
            # publish the frame and restore the framebuffer binding
            server.unbind_and_publish()
```

For scenes that need smoother edges or depth and stencil buffers, the server accepts `antialias_sample_count`, `depth_buffer_resolution`, and `stencil_buffer_resolution`. These options are disabled by default; the driver chooses a supported configuration. Supported parameter values are listed in `syphon.server.SyphonOpenGLServer`.

Only unbind after a successful bind, and do both on the same thread. The OpenGL context must remain alive and available exclusively to that thread during drawing. Unbind before stopping the server.

See [OpenGLDirectRenderingExample](https://github.com/cansik/syphon-python/blob/main/examples/OpenGLDirectRenderingExample.py) for a complete example which creates its own context.

## Resource Cleanup

Clients and servers hold native resources while they are running. A `with` statement is a convenient way to release them when leaving a block, including when an exception occurs.

```python
with syphon.SyphonMetalServer("Demo") as server:
    ...  # create and publish textures

# the server has now been stopped
```

The same pattern works for clients. Calling `stop()` explicitly is also supported, and calling it more than once is harmless.

### Removing Directory Observers

An application may only need discovery notifications while a server-selection view is open. `add_observer()` returns a token which can be used to remove that subscription when it is no longer needed.

```python
with syphon.SyphonServerDirectory() as directory:
    # listen for newly available servers
    token = directory.add_observer(syphon.SyphonServerNotification.Announce, print)
    directory.update_run_loop()

    # stop receiving this notification
    directory.remove_observer(token)
```

Leaving the `with` block removes any remaining observers registered through that directory wrapper. Alternatively, call `directory.close()` explicitly. This does not stop Syphon's shared directory or remove another wrapper's observers.

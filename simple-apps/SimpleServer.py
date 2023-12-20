# OpenGL/Metal rendering test: render a spinning cube with a perspective
# example used from nanogui
# https://github.com/mitsuba-renderer/nanogui/blob/master/src/python/render_test_2.py
import ctypes
import sys
from typing import Any

import objc

sys.path.append('python')
import nanogui
from nanogui import Shader, RenderPass, Screen, Matrix4f
from nanogui import glfw
import numpy as np
import syphon


def get_mtl_texture(texture: Any) -> Any:
    ctypes.pythonapi.PyCapsule_GetName.restype = ctypes.c_char_p
    ctypes.pythonapi.PyCapsule_GetName.argtypes = [ctypes.py_object]
    capsule_name = ctypes.pythonapi.PyCapsule_GetName(texture)

    texture_c_ptr = ctypes.c_void_p()

    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
    result = ctypes.pythonapi.PyCapsule_GetPointer(texture, capsule_name)

    texture_c_ptr.value = result

    mtl_texture = objc.objc_object(c_void_p=result)
    return mtl_texture


class SimpleServerScreen(Screen):
    def __init__(self):
        Screen.__init__(self,
                        size=[640, 480],
                        caption="Syphon-Python Simple Server",
                        depth_buffer=True,
                        resizable=False
                        )

        if nanogui.api != "metal":
            print("This application only runs on metal!")
            exit(1)

        self.syphon_server = syphon.SyphonMetalServer("simple")

        vertex_program = '''
            using namespace metal;

            struct VertexOut {
                float4 position [[position]];
                float4 color;
            };

            vertex VertexOut vertex_main(const device packed_float3 *position,
                                         const device float4 *color,
                                         constant float4x4 &mvp,
                                         uint id [[vertex_id]]) {
                VertexOut vert;
                vert.position = mvp * float4(position[id], 1.f);
                vert.color = color[id];
                return vert;
            }
        '''

        fragment_program = '''
            using namespace metal;

            struct VertexOut {
                float4 position [[position]];
                float4 color;
            };

            fragment float4 fragment_main(VertexOut vert [[stage_in]]) {
                return vert.color;
            }
        '''

        self.render_pass = RenderPass(
            color_targets=[self],
            depth_target=self
        )

        self.shader = Shader(
            self.render_pass,
            "test_shader",
            vertex_program,
            fragment_program
        )

        p = np.array([
            [-1, 1, 1], [-1, -1, 1],
            [1, -1, 1], [1, 1, 1],
            [-1, 1, -1], [-1, -1, -1],
            [1, -1, -1], [1, 1, -1]],
            dtype=np.float32
        )

        color = np.array([
            [0, 1, 1, 1], [0, 0, 1, 1],
            [1, 0, 1, 1], [1, 1, 1, 1],
            [0, 1, 0, 1], [0, 0, 0, 1],
            [1, 0, 0, 1], [1, 1, 0, 1]],
            dtype=np.float32
        )

        indices = np.array([
            3, 2, 6, 6, 7, 3,
            4, 5, 1, 1, 0, 4,
            4, 0, 3, 3, 7, 4,
            1, 5, 6, 6, 2, 1,
            0, 1, 2, 2, 3, 0,
            7, 6, 5, 5, 4, 7],
            dtype=np.uint32
        )

        self.shader.set_buffer("position", p)
        self.shader.set_buffer("color", color)
        self.shader.set_buffer("indices", indices)

    def draw_contents(self):
        with self.render_pass:
            view = Matrix4f.look_at(
                origin=[0, -2, -10],
                target=[0, 0, 0],
                up=[0, 1, 0]
            )

            model = Matrix4f.rotate(
                [0, 1, 0],
                glfw.getTime()
            )

            fbsize = self.framebuffer_size()
            proj = Matrix4f.perspective(
                fov=25 * np.pi / 180,
                near=0.1,
                far=20,
                aspect=fbsize[0] / float(fbsize[1])
            )

            mvp = proj @ view @ model
            self.shader.set_buffer("mvp", mvp.T)
            with self.shader:
                self.shader.draw_array(Shader.PrimitiveType.Triangle,
                                       0, 36, indexed=True)

        texture = self.metal_texture()  # of type PyCapsule
        texture_pointer = get_mtl_texture(texture)
        self.syphon_server.publish_frame_texture(texture_pointer, is_flipped=True)

    def keyboard_event(self, key, scancode, action, modifiers):
        if super(SimpleServerScreen, self).keyboard_event(key, scancode,
                                                          action, modifiers):
            return True
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            self.set_visible(False)
            return True
        return False

    def resize_event(self, size):
        self.render_pass.resize(self.framebuffer_size())
        super(SimpleServerScreen, self).resize_event(size)
        return True


def main():
    nanogui.init()
    s = SimpleServerScreen()
    s.set_visible(True)
    nanogui.mainloop(1 / 60.0 * 1000)
    nanogui.shutdown()
    s.syphon_server.stop()
    exit(0)


if __name__ == "__main__":
    main()

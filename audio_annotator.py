import copy

import matplotlib.pyplot as plt
import numpy as np
import enum
import sounddevice as sd

from area_rectangle import AreaRectangle
from matplotlib.backend_tools import Cursors

from game_resource_explorer import GameResourceExplorer

"""
Parameters
----------
s : str
    One of the following events ids:

    - 'button_press_event'
    - 'button_release_event'
    - 'draw_event'
    - 'key_press_event'
    - 'key_release_event'
    - 'motion_notify_event'
    - 'pick_event'
    - 'resize_event'
    - 'scroll_event'
    - 'figure_enter_event',
    - 'figure_leave_event',
    - 'axes_enter_event',
    - 'axes_leave_event'
    - 'close_event'.
"""

# These values reflect matplotlib's MouseButtons internal enum numbers
MOUSE_BUTTON_LEFT = 1
MOUSE_BUTTON_RIGHT = 3
ZOOM_STEP_SCALE = 0.15
MINIMUM_NEW_AREA_WIDTH_PIXELS = 5

class GUIState(enum.IntEnum):
    IDLE = enum.auto()
    NEW_AREA = enum.auto()
    MOVING_AREA = enum.auto()
    MOVING_EDGE = enum.auto()
    PANNING = enum.auto()

class AudioAnnotator:

    """
    Check:
    https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.Rectangle.html
    https://matplotlib.org/stable/gallery/event_handling/looking_glass.html
    https://pypi.org/project/PyAudio/

    # Matplotlib drawing performance
    https://stackoverflow.com/questions/8955869/why-is-plotting-with-matplotlib-so-slow

    [NOTES]
    - all x and y values/positions are "xdata"
    """

    def __init__(self):

        self.fig = plt.figure(figsize=(16, 8))
        self.top_axis = self.fig.add_subplot(2, 1, 1)
        self.bottom_axis = self.fig.add_subplot(2, 1, 2)
        self.bottom_signal_handle = None

        self.data_y = None
        self.data_x = None
        self.sampling_freq = 1

        self.state = GUIState.IDLE

        # List of areas
        self.areas = []
        self.current_zoom = 1.0
        self.zoom_step_scale = ZOOM_STEP_SCALE
        self.data_x_min = 0.0
        self.data_x_max = 1.0

        # Panning action
        self.panning_x_min_original = 0
        self.panning_x_max_original = 0
        self.panning_mouse_x = 0

        # Mouse buttons
        self.mouse_left_down = False
        self.mouse_right_down = False

        # Key modifiers
        self.key_ctrl_down = False
        self.key_shift_down = False
        self.key_alt_down = False

        self.background = self.fig.canvas.copy_from_bbox(self.top_axis.bbox)

        # Attach callbacks
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.fig.canvas.mpl_connect('key_release_event', self.on_key_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_move)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

    def on_press(self, event):

        if event.button == MOUSE_BUTTON_LEFT:
            self.mouse_left_down = True

        if event.button == MOUSE_BUTTON_RIGHT:
            self.mouse_right_down = True

        mouse_x = event.xdata
        mouse_x_pixels = event.x

        for area in self.areas:
            area.deselect()

        if self.state == GUIState.IDLE and self.mouse_left_down and mouse_x is not None:

            # TODO: Simplify hovering areas pre-selection
            # Get all areas under the mouse
            hovering_areas = [area for area in self.areas if area.is_hovering(x=mouse_x, y=0)]

            # Mark all areas under the mouse
            for area in hovering_areas:
                area.select(mouse_x=mouse_x)

            selected_areas = self.get_selected_areas()

            # Update all mouse offsets for all selected areas
            any_hovering_edges = False
            for area in selected_areas:
                area.update_select_offset(mouse_x=mouse_x)

            for area in self.areas:
                edge = area.is_hovering_edge(x_pixels=mouse_x_pixels)
                if edge == 'left':
                    area.select(mouse_x=mouse_x)
                    area._left_edge_selected = True
                    any_hovering_edges = True
                elif edge == 'right':
                    area.select(mouse_x=mouse_x)
                    area._right_edge_selected = True
                    any_hovering_edges = True

            if any_hovering_edges:
                self.state = GUIState.MOVING_EDGE

            else:

                if len(selected_areas) == 0 and mouse_x is not None:

                    # CREATE NEW AREA
                    self.state = GUIState.NEW_AREA
                    new_area = AreaRectangle(x=mouse_x, y=-1, width=0.001, height=2)
                    new_area.attach(axis=self.top_axis)
                    new_area.select(mouse_x=mouse_x)
                    new_area.set_x(x=mouse_x)
                    self.areas.append(new_area)

                else:

                    # MOVE SELECTED AREAS
                    self.state = GUIState.MOVING_AREA
                    for area in selected_areas:
                        area.set_x(x=mouse_x, with_offset=True)

                    # UPDATE SIGNAL ON BOTTON AXIS
                    selected_area = selected_areas[0]
                    index_start = int(np.round(selected_area.x))
                    index_stop = int(np.round(selected_area.x + selected_area.width))
                    self._update_bottom_axis(signal_index_start=index_start,
                                             signal_index_stop=index_stop)

        if self.state == GUIState.IDLE and self.mouse_right_down and mouse_x is not None:

            self.state = GUIState.PANNING
            self.panning_mouse_x = mouse_x
            self.panning_x_min_original = self.top_axis.viewLim.x0
            self.panning_x_max_original = self.top_axis.viewLim.xmax
            self.fig.canvas.set_cursor(Cursors.MOVE)

        self.update_plot()

    def on_move(self, event):

        mouse_x = event.xdata
        mouse_x_pixels = event.x

        any_hovering_edges = False
        for area in self.areas:
            edge = area.is_hovering_edge(x_pixels=mouse_x_pixels)
            if edge == 'left' or edge == 'right':
                any_hovering_edges = True

        if self.state == GUIState.NEW_AREA:
            for area in self.get_selected_areas():
                area.set_x_max(x=mouse_x)

        if self.state == GUIState.PANNING:

            if mouse_x is not None:
                delta = self.panning_mouse_x - mouse_x
                x_min = self.top_axis.viewLim.x0 + delta
                x_max = self.top_axis.viewLim.xmax + delta
                if x_min >= self.data_x_min and x_max <= self.data_x_max:
                    self.top_axis.set_xlim(x_min, x_max)

        if self.state == GUIState.IDLE or self.state == GUIState.MOVING_EDGE:

            # Change mouse cursor when hovering edges
            if any_hovering_edges:
                self.fig.canvas.set_cursor(Cursors.RESIZE_HORIZONTAL)
            else:
                self.fig.canvas.set_cursor(Cursors.POINTER)

        if self.state == GUIState.MOVING_EDGE:
            for area in self.areas:
                if area._left_edge_selected:
                    area.set_x_min(x=mouse_x)
                if area._right_edge_selected:
                    area.set_x_max(x=mouse_x)

        if self.state == GUIState.MOVING_AREA:
            for area in self.get_selected_areas():
                area.set_x(x=mouse_x, with_offset=True)

        self.update_plot()

    def on_release(self, event):

        if event.button == MOUSE_BUTTON_LEFT:
            self.mouse_left_down = False

        if event.button == MOUSE_BUTTON_RIGHT:
            self.mouse_right_down = False

        if self.state == GUIState.NEW_AREA:
            if len(self.areas) > 0:
                new_area = self.areas[-1]
                new_area.fix_negative_width()
                delta = new_area.get_x_max_pixels() - new_area.get_x_min_pixels()

                # Delete current area if area is too narrow
                if delta < MINIMUM_NEW_AREA_WIDTH_PIXELS:
                    new_area.set_visible(False)
                    self.areas.remove(new_area)

        selected_areas = self.get_selected_areas()

        if self.state == GUIState.MOVING_EDGE:
            for area in selected_areas:
                area.fix_negative_width()

        if self.bottom_signal_handle is not None and (self.state in [GUIState.NEW_AREA, GUIState.MOVING_EDGE, GUIState.MOVING_AREA]):
            if len(selected_areas) > 0:
                selected_area = selected_areas[0]
                index_start = int(np.round(selected_area.x))
                index_stop = int(np.round(selected_area.x + selected_area.width))
                self._update_bottom_axis(signal_index_start=index_start,
                                         signal_index_stop=index_stop)

        if self.state == GUIState.PANNING:
            self.fig.canvas.set_cursor(Cursors.POINTER)

        for area in self.areas:
            area._left_edge_selected = False
            area._right_edge_selected = False

        self.state = GUIState.IDLE
        self.update_plot()

    def on_scroll(self, event):

        mouse_x = event.xdata
        if mouse_x is None:
            return

        # Update zoom level
        self.current_zoom += event.step

        # Get relevant values
        x_min = self.top_axis.viewLim.x0
        x_max = self.top_axis.viewLim.xmax

        # Update axis X limit values
        x_min += event.step * self.zoom_step_scale * (mouse_x - x_min)
        x_max -= event.step * self.zoom_step_scale * (x_max - mouse_x)

        # Apply correction if limits go outside data bounds
        x_min = x_min if x_min > self.data_x_min else self.data_x_min
        x_max = x_max if x_max < self.data_x_max else self.data_x_max

        # Update axis limits
        self.top_axis.set_xlim(x_min, x_max)
        self.update_plot()

    def on_key_press(self, event):

        # Update modifiers' states
        if event.key == 'shift':
            self.key_shift_down = True
        if event.key == 'control':
            self.key_shift_down = True
        if event.key == 'alt':
            self.key_shift_down = True

        # Arrow keys
        if event.key == 'left':

            pass
        if event.key == 'right':
            pass


        if event.key == 'delete':
            areas_to_be_deleted = [area for area in self.get_selected_areas()]
            for area in areas_to_be_deleted:
                area.set_visible(False)
                self.areas.remove(area)
            self.update_plot()


        if event.guiEvent.keysym == 'space':
            # Play selected sound
            selected_areas = [area for area in self.get_selected_areas()]
            if len(selected_areas) > 0:
                index_start = int(np.round(selected_areas[0].x))
                index_stop = int(np.round(index_start + selected_areas[0].width))
                print('Playing Sound')
                sd.play(self.data_y[index_start:index_stop], self.sampling_freq)


    def on_key_release(self, event):
        if event.key == 'shift':
            self.key_shift_down = False
        if event.key == 'control':
            self.key_shift_down = False
        if event.key == 'alt':
            self.key_shift_down = False

    # ============================================================
    #                       Axis Updates
    # ============================================================

    def _update_bottom_axis(self, signal_index_start: int, signal_index_stop: int):
        selected_data_x = self.data_x[signal_index_start:signal_index_stop]
        selected_data_y = self.data_y[signal_index_start:signal_index_stop]
        self.bottom_signal_handle.set_data(selected_data_x, selected_data_y)
        self.bottom_axis.set_xlim(self.data_x[signal_index_start], self.data_x[signal_index_stop - 1])

    def update_plot(self):
        self.fig.canvas.draw()
        #self.fig.canvas.restore_region(self.background)
        #for area in self.areas:
        #    self.top_axis.draw_artist(area._handle)
        #    self.fig.canvas.blit(self.top_axis.bbox)

    # ============================================================
    #                       Getters
    # ============================================================

    def get_selected_areas(self):
        return [area for area in self.areas if area._selected]

    def get_hovering_area(self, x: float):
        for area_handle in self.areas:
            x_min = area_handle.get_x()
            x_max = x_min + area_handle._width
            if x_min < x < x_max:
                return area_handle
        return None

    def build_annotation_blueprint(self) -> dict:

        blueprint = dict()
        blueprint['labels'] = []
        #for area in self.areas:
        #    blueprint['labels'] = {
        #        'name': area.name
        #    }

        return blueprint

    def annotate(self, signal: np.array, sampling_freq: float, title='No Title') -> dict:

        self.data_x = np.arange(signal.size)
        self.data_y = signal
        self.sampling_freq = sampling_freq

        # Update X Axis data range
        self.data_x_min = np.min(self.data_x)
        self.data_x_max = np.max(self.data_x)

        self.top_axis.plot(signal, linewidth=1)
        self.top_axis.set_xlim(self.data_x_min, self.data_x_max)
        self.top_axis.set_ylim(np.min(signal), np.max(signal))
        self.top_axis.set_title(title)
        self.top_axis.set_ylabel('Signal Value')
        self.top_axis.set_xlabel('Signal Samples')

        self.bottom_signal_handle,  = self.bottom_axis.plot(signal)

        self.background = self.fig.canvas.copy_from_bbox(self.top_axis.bbox)

        # All annotation happens here because of the callbacks
        plt.show()

        # Now you can build the dictionary with
        annotation_blueprint = self.build_annotation_blueprint()

        return annotation_blueprint


if __name__ == "__main__":

    explorer = GameResourceExplorer()
    hdf5_fpath = "D:\game_resource_archive_hdf5\game_0039.hdf5"
    audio_files = explorer.get_game_audio_file_list(hdf5_fpath=hdf5_fpath)
    samples, freq = explorer.get_audio_data(hdf5_fpath=hdf5_fpath, audio_file=audio_files['bgv'][2])

    # Create Demo Data
    t = np.arange(0.0, 2.0, 0.01)
    s3 = np.sin(4 * np.pi * t)

    span = AudioAnnotator()
    span.annotate(signal=samples, sampling_freq=freq)

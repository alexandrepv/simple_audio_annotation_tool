import enum
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import SpanSelector
from game_resource_explorer import GameResourceExplorer

# These values reflect matplotlib's MouseButtons internal enum numbers
MOUSE_BUTTON_LEFT = 1
MOUSE_BUTTON_RIGHT = 3
ZOOM_STEP_SCALE = 0.1
MINIMUM_NEW_AREA_WIDTH_PIXELS = 5


class GUIState(enum.IntEnum):
    IDLE = enum.auto()
    NEW_AREA = enum.auto()
    MOVING_AREA = enum.auto()
    MOVING_EDGE = enum.auto()
    PANNING = enum.auto()


class AudioAnnotator2:

    """
    This is a different take on the same annotator, but using SpanSelector instead of rectangles
    Code inspired by: https://matplotlib.org/2.0.2/examples/widgets/span_selector.html
    """

    def __init__(self):

        self.fig = plt.figure(figsize=(8, 4))
        self.top_axis = self.fig.add_subplot(2, 1, 1)
        self.bottom_axis = self.fig.add_subplot(2, 1, 2)
        self.bottom_signal_handle = None

        self.data_y = None
        self.data_x = None

        self.state = GUIState.IDLE

        # List of areas
        self.spans = []
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

        # TESTING AN IDEA
        new_span = SpanSelector(self.top_axis,
                                self.onselect,
                                'horizontal',
                                useblit=True,
                                interactive=True,
                                drag_from_anywhere=True,
                                ignore_event_outside=True,
                                rectprops=dict(alpha=0.5, facecolor='red'))
        self.spans.append(new_span)

        # Attach callbacks
        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)

    def onselect(self, xmin, xmax):
        print('Moved!')
        pass

    def on_press(self, event):

        pass

    def on_release(self, event):
        new_span = SpanSelector(self.top_axis,
                                self.onselect,
                                'horizontal',
                                useblit=True,
                                interactive=True,
                                drag_from_anywhere=True,
                                ignore_event_outside=True,
                                rectprops=dict(alpha=0.5, facecolor='red'))
        self.spans.append(new_span)
        print('Released!')
        pass


    def annotate(self, signal: np.array, title='No Title'):
        self.data_x = np.arange(signal.size)
        self.data_y = signal

        # Update X Axis data range
        self.data_x_min = np.min(self.data_x)
        self.data_x_max = np.max(self.data_x)

        self.top_axis.plot(signal, linewidth=1)
        self.top_axis.set_xlim(self.data_x_min, self.data_x_max)
        self.top_axis.set_ylim(np.min(signal), np.max(signal))
        self.top_axis.set_title(title)
        self.top_axis.set_ylabel('Signal Value')
        self.top_axis.set_xlabel('Signal Samples')

        self.bottom_signal_handle, = self.bottom_axis.plot(signal)

        # All annotation happens here because of the callbacks
        plt.show()


if __name__ == "__main__":

    explorer = GameResourceExplorer()
    hdf5_fpath = "D:\game_resource_archive_hdf5\game_0039.hdf5"
    audio_files = explorer.get_game_audio_file_list(hdf5_fpath=hdf5_fpath)
    y, freq = explorer.get_audio_data(hdf5_fpath=hdf5_fpath, audio_file=audio_files['bgv'][2])
    x = np.arange(y.size)

    annotator = AudioAnnotator2()
    annotator.annotate(signal=y)
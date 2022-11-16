import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

DEFAULT_STATE = 'idle'
DEFAULT_EDGE_GRAB_MARGIN = 5

"""
[ Useful Links ]
https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.Rectangle.html
https://matplotlib.org/stable/gallery/widgets/mouse_cursor.html
https://stackoverflow.com/questions/21687571/matplotlib-remove-patches-from-figure
"""

class AreaRectangle:

    def __init__(self,
                 x: float,
                 y: float,
                 width: float,
                 height: float,
                 edge_grab_offset_pixels_x=DEFAULT_EDGE_GRAB_MARGIN,
                 edge_grab_offset_pixels_y=DEFAULT_EDGE_GRAB_MARGIN):

        self._label = ''
        self._handle = None  # Matplotlib handle
        self._attached = False
        self._selected = False
        self._left_edge_selected = False
        self._right_edge_selected = False
        self.stage = DEFAULT_STATE

        # Dimension and position
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.edge_grab_offset_pixels_x = edge_grab_offset_pixels_x
        self.edge_grab_offset_pixels_y = edge_grab_offset_pixels_y

        # Color variables
        self.idle_color = 'b'
        self.idle_color_alpha = 0.3
        self.selected_color = 'r'
        self.selected_color_alpha = 0.3

    def __del__(self):
        # Detach automatically if still attached
        if self._handle is not None and self._attached:
            self._handle.remove()

    def select(self, mouse_x: float):
        if self._handle is not None:
            self.mouse_offset_x = self.x - mouse_x  # Record the current mouse offset at time of selection
            self._handle.set(color=self.selected_color)
            self._selected = True

    def update_select_offset(self, mouse_x):
        self.mouse_offset_x = self.x - mouse_x

    def deselect(self):
        if self._handle is not None:
            self._handle.set(color=self.idle_color)
            self._selected = False

    def attach(self, axis: plt.Axes):
        """
        You need to attach this rectangle to the axis to make it work
        :param axis:
        :return:
        """
        self._handle = Rectangle(
            xy=(self.x, self.y),
            width=self.width,
            height=2,
            facecolor=self.idle_color,
            alpha=self.idle_color_alpha
        )
        axis.add_patch(self._handle)
        self._attached = True

    def get_x_min_pixels(self) -> float:
        if self._handle is not None:
            return self._handle.get_extents().x0
        return 0

    def get_x_max_pixels(self) -> float:
        if self._handle is not None:
            return self._handle.get_extents().xmax
        return 0

    def is_hovering(self, x, y):

        if x is None or y is None:
            return False

        # TODO use built-in function get_hovering when using the event
        if self.x <= x <= (self.x + self.width) and self.y <= y <= (self.y + self.height):
            return True
        return False

    def is_hovering_edge(self, x_pixels):
        if self._handle is not None:
            bbox = self._handle.get_extents()
            delta = np.abs(bbox.x0 - x_pixels)
            if delta < self.edge_grab_offset_pixels_x:
                return 'left'
            delta = np.abs(bbox.xmax - x_pixels)
            if delta < self.edge_grab_offset_pixels_x:
                return 'right'
        return None

    def set_x_min(self, x: float):
        if self._handle is not None and x is not None:
            self.width = self.x + self.width - x
            self.x = x
            self._handle.set_width(self.width)
            self._handle.set_x(self.x)

    def set_x_max(self, x: float):
        if self._handle is not None and x is not None:
            self.width = x - self.x
            self._handle.set_width(self.width)

    def set_x(self, x: float, with_offset=False):
        if self._handle is not None and x is not None:
            self.x = x if not with_offset else x + self.mouse_offset_x
            self._handle.set_x(self.x)

    def set_width(self, width: float):
        if self._handle is not None and width is not None:
            self.width = width
            self._handle.set_width(self.width)

    def set_visible(self, status=True):
        if self._handle is not None:
            self._handle.set(visible=status)

    def fix_negative_width(self):

        # It is possible to move the right edge to the left of the left edge,
        # thus making the width negative. This function swaps the edge to make
        # sure the left edge has always a smaller x value compared to the right
        # edge

        if self.width < 0:

            # Fix internal data
            self.x = self.x + self.width
            self.width = np.abs(self.width)

            # Fix plot representation, if available
            if self._handle is not None:
                self._handle.set_x(self.x)
                self._handle.set_width(self.width)

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

DEFAULT_STATE = 'idle'
DEFAULT_EDGE_GRAB_MARGIN = 5
DEFAULT_ALPHA = 0.3
DEFAULT_IDLE_COLOR = (0, 0, 1)
DEFAULT_IDLE_EDGE_COLOR = (.25, .25, .75)
DEFAULT_SELECTED_COLOR = (1, 0, 0)
DEFAULT_SELECTED_EDGE_COLOR = (0.75, .25, .25)
DEFAULT_ACTIVE_COLOR = 'r'
DEFAULT_ACTIVE_EDGE_COLOR = 'r'
DEFAULT_EDGE_WIDTH = 2
DEFAULT_LABEL_FONT_SIZE = 25

"""
[ Useful Links ]
https://matplotlib.org/stable/api/_as_gen/matplotlib.patches.Rectangle.html
https://matplotlib.org/stable/gallery/widgets/mouse_cursor.html
https://stackoverflow.com/questions/21687571/matplotlib-remove-patches-from-figure
"""

class Annotation:

    def __init__(self,
                 label='',
                 x_min=0,
                 x_max=0,
                 y_min=0,
                 y_max=0,
                 edge_grab_offset_pixels_x=DEFAULT_EDGE_GRAB_MARGIN,
                 edge_grab_offset_pixels_y=DEFAULT_EDGE_GRAB_MARGIN):

        self.label = label
        self.rect_handle = None  # Matplotlib handle
        self.text_handle = None  # Matplotlib handle
        self.active = False
        self.selected = False
        self.hovering = False
        self.moving = False
        self.attached_to_axis = False
        self.left_edge_hovering = False
        self.right_edge_hovering = False
        self.left_edge_active = False
        self.right_edge_active = False

        # Dimension and position
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.edge_grab_offset_pixels_x = edge_grab_offset_pixels_x
        self.edge_grab_offset_pixels_y = edge_grab_offset_pixels_y
        self.mouse_offset_x_min = 0

        # Color variables
        self.idle_color = DEFAULT_IDLE_COLOR
        self.idle_edge_color = DEFAULT_IDLE_EDGE_COLOR
        self.idle_alpha = DEFAULT_ALPHA
        self.selected_color = DEFAULT_SELECTED_COLOR
        self.selected_idle_color = DEFAULT_SELECTED_COLOR
        self.selected_alpha = 0.3

    def __del__(self):
        # Detach automatically if still attached
        if self.rect_handle is not None and self.attached_to_axis:
            self.rect_handle.remove()

        if self.text_handle is not None and self.attached_to_axis:
            self.text_handle.remove()

    # ===========================================================
    #                      Update Functions
    # ===========================================================

    def update_select_offset(self, x):
        self.mouse_offset_x_min = self.x_min - x

    def update_plot_elements(self):
        if self.rect_handle is None:
            return

        self.rect_handle.set_x(self.get_rect_x())
        self.rect_handle.set_width(self.get_rect_width())

        if self.selected:
            self.rect_handle.set(color=DEFAULT_SELECTED_COLOR, edgecolor=DEFAULT_SELECTED_EDGE_COLOR)
        elif self.active:
            self.rect_handle.set(edgecolor=DEFAULT_ACTIVE_EDGE_COLOR)
        else:
            self.rect_handle.set(color=DEFAULT_IDLE_COLOR, edgecolor=DEFAULT_IDLE_EDGE_COLOR)

        self.text_handle.set(x=self.get_x_center())

    def update_hovering(self, x_pixels: float):
        if self.rect_handle is not None:
            bbox = self.rect_handle.get_extents()

            if bbox.x0 <= x_pixels <= bbox.xmax:
                self.hovering = True
            else:
                self.hovering = False

            delta = np.abs(bbox.x0 - x_pixels)
            if delta < self.edge_grab_offset_pixels_x:
                self.left_edge_hovering = True
            else:
                self.left_edge_hovering = False

            delta = np.abs(bbox.xmax - x_pixels)
            if delta < self.edge_grab_offset_pixels_x:
                self.right_edge_hovering = True
            else:
                self.right_edge_hovering = False

    def update_activated_edges(self):
        if self.left_edge_hovering:
            self.left_edge_active = True
        if self.right_edge_hovering:
            self.right_edge_active = True

    # ===========================================================
    #                           Utility
    # ===========================================================

    def activate(self, x: float):
        self.mouse_offset_x_min = self.x_min - x  # Record the current mouse offset at time of selection
        self.selected = True
        self.active = True

    def deselect(self):
        self.active = False
        self.selected = False

    def deactivate(self):
        self.active = False

    def attach_to_axis(self, axis: plt.Axes):

        self.rect_handle = Rectangle(
            xy=self.get_rect_xy(),
            width=self.get_rect_width(),
            height=self.get_rect_height(),
            facecolor=self.idle_color,
            alpha=self.idle_alpha,
            edgecolor=None,
            linewidth=DEFAULT_EDGE_WIDTH,
            zorder=1
        )

        self.text_handle = axis.text(
            self.get_x_center(),
            self.get_y_center(),
            self.label,
            size=DEFAULT_LABEL_FONT_SIZE,
            ha="center",
            va="center",
            clip_on=True
        )

        axis.add_patch(self.rect_handle)
        self.attached_to_axis = True

    def fix_min_and_max(self):
        if self.x_max < self.x_min:
            self.x_min, self.x_max = self.x_max, self.x_min

        if self.rect_handle is not None:
            self.rect_handle.set_x(self.get_rect_x())
            self.rect_handle.set_width(self.get_rect_width())

    # ===========================================================
    #                           Setters
    # ===========================================================

    def set_label(self, label: str):
        self.label = label

    def deactivate_edges(self):
        self.left_edge_active = False
        self.right_edge_active = False

    def move_x_range(self, new_x_min: float, include_offset=True):
        width = self.x_max - self.x_min
        self.x_min = new_x_min + self.mouse_offset_x_min if include_offset else new_x_min
        self.x_max = self.x_min + width

    def increment_x(self, delta_x):
        self.x_min += delta_x
        self.x_max += delta_x

    def decrement_x(self, delta_x):
        self.x_min -= delta_x
        self.x_max -= delta_x

    def set_x_min(self, x: float, valid_range=None) -> None:
        if valid_range is None:
            self.x_min = x
        else:
            self.xmin = np.clip(x, a_min=valid_range[0], a_max=valid_range[1])
        self.rect_handle.set_x(self.get_rect_x())
        self.rect_handle.set_width(self.get_rect_width())

    def set_x_max(self, x: float, valid_range=None):
        if valid_range is None:
            self.x_max = x
        else:
            self.x_max = np.clip(x, a_min=valid_range[0], a_max=valid_range[1])
        self.rect_handle.set_width(self.get_rect_width())
        self.rect_handle.set_x(self.get_rect_x())

    def set_visible(self, status=True):
        if self.rect_handle is not None:
            self.rect_handle.set(visible=status)

    # ===========================================================
    #                           Getters
    # ===========================================================

    def get_x_min(self) -> float:
        return self.x_min

    def get_x_max(self) -> float:
        return self.x_max

    def get_x_center(self):
        return (self.x_min + self.x_max) * 0.5

    def get_y_center(self):
        return (self.y_min + self.y_max) * 0.5

    def get_rect_x(self) -> float:
        return self.x_min

    def get_rect_xy(self) -> tuple:
        return self.x_min, self.y_min

    def get_rect_width(self) -> float:
        return self.x_max - self.x_min

    def get_rect_height(self) -> float:
        return self.y_max - self.y_min

    def get_rect_color(self):
        if self.active:
            return self.idle_color

    def get_x_min_pixels(self) -> float:
        if self.rect_handle is not None:
            return self.rect_handle.get_extents().x0
        return 0

    def get_x_max_pixels(self) -> float:
        if self.rect_handle is not None:
            return self.rect_handle.get_extents().xmax
        return 0

    def is_edge_hovering(self) -> bool:
        return self.left_edge_hovering or self.right_edge_hovering

    def is_hovering(self, x: float, y: float) -> bool:

        if x is None or y is None:
            return False

        # TODO use built-in function get_hovering when using the event
        if self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max:
            return True
        return False
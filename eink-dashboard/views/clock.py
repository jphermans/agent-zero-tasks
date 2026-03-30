"""
Clock view for e-ink dashboard.
Displays a large digital clock with date and day of week.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging
from datetime import datetime

from renderer import (
    create_canvas,
    draw_header,
    draw_footer,
    draw_centered_text,
    get_font,
    WIDTH,
    HEIGHT,
    TEXT_COLOR,
    MUTED_COLOR,
    ACCENT_COLOR,
)

logger = logging.getLogger(__name__)


class ClockView:
    """Full-screen digital clock display."""

    def __init__(self, config=None, service=None):
        self.config = config or {}

    def render(self):
        """
        Render the clock view.

        Returns:
            PIL.Image - rendered clock screen
        """
        try:
            img, draw = create_canvas()

            now = datetime.now()

            # Header
            draw_header(draw, "Clock", now.strftime("%A"))

            # Large time display centered vertically
            time_str = now.strftime("%H:%M")
            time_font = get_font(72, bold=True)
            y_center = (HEIGHT - 28 - 52) // 2  # account for header/footer
            y_start = 52 + y_center - 50

            y = draw_centered_text(draw, time_str, y_start, time_font, TEXT_COLOR)

            # Seconds in smaller text
            sec_str = now.strftime(":%S")
            sec_font = get_font(28)
            y = draw_centered_text(draw, sec_str, y + 8, sec_font, MUTED_COLOR)

            # Full date below
            date_str = now.strftime("%B %d, %Y")
            date_font = get_font(28)
            draw_centered_text(draw, date_str, y + 12, date_font, TEXT_COLOR)

            # Day of week at bottom area
            day_str = now.strftime("%A")
            day_font = get_font(22)
            draw_centered_text(draw, day_str, y + 50, day_font, MUTED_COLOR)

            # Footer
            draw_footer(draw, f"Updated: {now.strftime('%H:%M:%S')}")

            return img

        except Exception as e:
            logger.error(f"Error rendering clock view: {e}")
            # Return a valid error image
            img, draw = create_canvas()
            draw_header(draw, "Clock", "Error")
            error_font = get_font(20)
            draw_centered_text(draw, "Clock error", 200, error_font, TEXT_COLOR)
            draw_footer(draw, "Error")
            return img

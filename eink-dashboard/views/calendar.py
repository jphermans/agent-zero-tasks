"""
Calendar view for e-ink dashboard.
Displays today's Google Calendar events with times and locations.
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
    draw_text_block,
    draw_divider,
    get_font,
    WIDTH,
    HEIGHT,
    TEXT_COLOR,
    MUTED_COLOR,
    INFO_COLOR,
    WARNING_COLOR,
)

logger = logging.getLogger(__name__)


class CalendarView:
    """Displays upcoming calendar events."""

    def __init__(self, config=None, service=None):
        self.config = config or {}
        self.service = service

    def render(self):
        """
        Render the calendar view.

        Returns:
            PIL.Image - rendered calendar screen
        """
        try:
            img, draw = create_canvas()
            now = datetime.now()

            # Header with today's date
            subtitle = now.strftime("%b %d")
            draw_header(draw, "Calendar", subtitle)

            y = 62
            max_y = HEIGHT - 38  # above footer
            event_font = get_font(18, bold=True)
            time_font = get_font(14)
            loc_font = get_font(12)
            max_events = 8

            # Fetch events
            events = []
            if self.service:
                try:
                    events = self.service.get_events(max_results=max_events)
                except Exception as e:
                    logger.error(f"Error fetching calendar events: {e}")
                    events = []

            if not events:
                # No events message
                msg_font = get_font(24)
                y = draw_centered_text(
                    draw, "No events today", (HEIGHT - 80) // 2, msg_font, MUTED_COLOR
                )
                hint_font = get_font(16)
                draw_centered_text(draw, "Enjoy your free time!", y + 15, hint_font, MUTED_COLOR)
            else:
                # Draw events list
                today_str = now.strftime("%b %d")
                for i, event in enumerate(events[:max_events]):
                    if y > max_y - 50:
                        more_font = get_font(14)
                        remaining = len(events) - i
                        draw.text(
                            (20, y),
                            f"  +{remaining} more...",
                            fill=MUTED_COLOR,
                            font=more_font,
                        )
                        break

                    summary = event.get("summary", "No title")
                    start = event.get("start", "")
                    end = event.get("end", "")
                    location = event.get("location", "")

                    # Time column
                    time_str = f"{start}"
                    if end and end != start:
                        time_str += f" - {end}"
                    draw.text((20, y), time_str, fill=INFO_COLOR, font=time_font)

                    # Event name
                    y += 20
                    draw.text((20, y), summary, fill=TEXT_COLOR, font=event_font)

                    # Location if present
                    if location:
                        y += 22
                        # Truncate long locations
                        if len(location) > 50:
                            location = location[:47] + "..."
                        draw.text(
                            (35, y),
                            f"{location}",
                            fill=MUTED_COLOR,
                            font=loc_font,
                        )

                    y += 26

                    # Divider between events (skip for last one)
                    if i < len(events) - 1 and i < max_events - 1:
                        draw_divider(draw, y)
                        y += 8

            # Footer
            draw_footer(draw, f"{len(events)} events")
            return img

        except Exception as e:
            logger.error(f"Error rendering calendar view: {e}")
            img, draw = create_canvas()
            draw_header(draw, "Calendar", "Error")
            error_font = get_font(20)
            draw_centered_text(draw, "Failed to load calendar", 200, error_font, TEXT_COLOR)
            draw_footer(draw, "Error")
            return img

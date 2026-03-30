"""
Email view for e-ink dashboard.
Displays unread count and recent email senders with subjects.
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
    HIGHLIGHT_COLOR,
    SUCCESS_COLOR,
)

logger = logging.getLogger(__name__)


class EmailView:
    """Displays email inbox summary."""

    def __init__(self, config=None, service=None):
        self.config = config or {}
        self.service = service

    def render(self):
        """
        Render the email view.

        Returns:
            PIL.Image - rendered email screen
        """
        try:
            img, draw = create_canvas()
            now = datetime.now()

            # Header
            draw_header(draw, "Email", now.strftime("%H:%M"))

            y = 60
            max_y = HEIGHT - 38

            # Fetch data
            unread = 0
            senders = []
            if self.service:
                try:
                    unread = self.service.get_unread_count()
                except Exception as e:
                    logger.error(f"Error fetching unread count: {e}")
                try:
                    senders = self.service.get_recent_senders(5)
                except Exception as e:
                    logger.error(f"Error fetching recent senders: {e}")

            # Unread count - large prominent display
            count_font = get_font(48, bold=True)
            count_str = str(unread)
            y = draw_centered_text(draw, count_str, y + 10, count_font, HIGHLIGHT_COLOR)

            # Label
            label_font = get_font(18)
            label = "unread" if unread != 1 else "unread"
            y = draw_centered_text(draw, "Unread Messages", y + 2, label_font, TEXT_COLOR)

            y += 15
            draw_divider(draw, y)
            y += 10

            # Recent senders list
            if senders:
                header_font = get_font(16, bold=True)
                draw.text((20, y), "Recent Emails", fill=TEXT_COLOR, font=header_font)
                y += 26

                sender_font = get_font(15, bold=True)
                subject_font = get_font(13)
                date_font = get_font(12)

                for i, sender in enumerate(senders):
                    if y > max_y - 40:
                        break

                    from_addr = sender.get("from", "Unknown")
                    subject = sender.get("subject", "(No subject)")
                    date = sender.get("date", "")

                    # Truncate long from addresses
                    if len(from_addr) > 35:
                        from_addr = from_addr[:32] + "..."

                    # Truncate long subjects
                    if len(subject) > 55:
                        subject = subject[:52] + "..."

                    # Sender name and date on same line
                    draw.text((25, y), from_addr, fill=TEXT_COLOR, font=sender_font)

                    # Date on right
                    if date:
                        bbox = draw.textbbox((0, 0), date, font=date_font)
                        dw = bbox[2] - bbox[0]
                        draw.text(
                            (WIDTH - dw - 20, y + 2),
                            date,
                            fill=MUTED_COLOR,
                            font=date_font,
                        )

                    y += 20

                    # Subject line
                    draw.text((35, y), subject, fill=MUTED_COLOR, font=subject_font)
                    y += 24

                    # Divider between senders
                    if i < len(senders) - 1:
                        draw_divider(draw, y)
                        y += 6

            else:
                no_email_font = get_font(16)
                draw_centered_text(
                    draw, "No recent emails", y + 20, no_email_font, MUTED_COLOR
                )

            # Footer
            draw_footer(draw, f"Inbox: {unread} unread")
            return img

        except Exception as e:
            logger.error(f"Error rendering email view: {e}")
            img, draw = create_canvas()
            draw_header(draw, "Email", "Error")
            error_font = get_font(20)
            draw_centered_text(draw, "Email display error", 200, error_font, TEXT_COLOR)
            draw_footer(draw, "Error")
            return img

"""
Home Assistant view for e-ink dashboard.
Displays smart home entity states in a grid layout.
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
    draw_divider,
    get_font,
    WIDTH,
    HEIGHT,
    TEXT_COLOR,
    MUTED_COLOR,
    INFO_COLOR,
    SUCCESS_COLOR,
    WARNING_COLOR,
    HIGHLIGHT_COLOR,
    BG_COLOR,
)

logger = logging.getLogger(__name__)


class HomeView:
    """Displays Home Assistant entity states in a grid."""

    def __init__(self, config=None, service=None):
        self.config = config or {}
        self.service = service

    def _get_friendly_name(self, entity):
        """Get friendly name from entity attributes."""
        attrs = entity.get("attributes", {})
        return attrs.get("friendly_name", entity.get("entity_id", "Unknown").split(".")[-1])

    def _get_unit(self, entity):
        """Get unit of measurement from entity attributes."""
        attrs = entity.get("attributes", {})
        return attrs.get("unit_of_measurement", "")

    def _get_domain(self, entity):
        """Extract domain from entity_id."""
        entity_id = entity.get("entity_id", "")
        return entity_id.split(".")[0] if "." in entity_id else "unknown"

    def _state_color(self, state, domain):
        """Choose display color based on state and domain."""
        if domain == "binary_sensor" or domain == "input_boolean":
            return SUCCESS_COLOR if state == "on" else MUTED_COLOR
        if domain == "light" or domain == "switch":
            return SUCCESS_COLOR if state == "on" else MUTED_COLOR
        if domain == "sensor":
            return INFO_COLOR
        if domain == "climate":
            return WARNING_COLOR
        return TEXT_COLOR

    def _format_state(self, entity):
        """Format entity state for display."""
        state = entity.get("state", "")
        domain = self._get_domain(entity)
        unit = self._get_unit(entity)

        if domain == "binary_sensor" or domain == "input_boolean":
            return "ON" if state == "on" else "OFF"
        if domain == "light" or domain == "switch":
            return "ON" if state == "on" else "OFF"
        if domain == "climate":
            return state.replace("_", " ").title()
        if unit:
            return f"{state} {unit}"
        return state

    def _draw_entity_card(self, draw, x, y, w, h, entity):
        """Draw a single entity card at the given position."""
        domain = self._get_domain(entity)
        friendly = self._get_friendly_name(entity)
        state = entity.get("state", "")
        formatted = self._format_state(entity)
        color = self._state_color(state, domain)

        # Card background border
        draw.rectangle([(x, y), (x + w, y + h)], outline=MUTED_COLOR, width=1)

        # Friendly name (truncated)
        name_font = get_font(11)
        if len(friendly) > 18:
            friendly = friendly[:15] + "..."
        draw.text((x + 6, y + 4), friendly, fill=MUTED_COLOR, font=name_font)

        # State value (large)
        state_font = get_font(18, bold=True)
        if len(formatted) > 12:
            state_font = get_font(14, bold=True)
        draw.text((x + 6, y + 20), formatted, fill=color, font=state_font)

        # Domain label at bottom
        domain_font = get_font(9)
        draw.text((x + 6, y + h - 14), domain, fill=MUTED_COLOR, font=domain_font)

    def render(self):
        """
        Render the home assistant view.

        Returns:
            PIL.Image - rendered home screen
        """
        try:
            img, draw = create_canvas()
            now = datetime.now()

            # Header
            draw_header(draw, "Home", now.strftime("%H:%M"))

            y = 58
            max_y = HEIGHT - 36

            # Fetch entities
            entities = []
            if self.service:
                try:
                    entities = self.service.get_entities()
                except Exception as e:
                    logger.error(f"Error fetching HA entities: {e}")

            if not entities:
                msg_font = get_font(24)
                y = draw_centered_text(
                    draw, "Home Assistant", (HEIGHT - 80) // 2 - 10, msg_font, MUTED_COLOR
                )
                hint_font = get_font(16)
                draw_centered_text(
                    draw, "No entities configured", y + 10, hint_font, MUTED_COLOR
                )
                sub_font = get_font(14)
                draw_centered_text(
                    draw, "Check HA URL and token", y + 35, sub_font, MUTED_COLOR
                )
                draw_footer(draw, "No data")
                return img

            # Grid layout: 3 columns
            cols = 3
            margin = 10
            card_w = (WIDTH - margin * (cols + 1)) // cols
            card_h = 60
            col_x = [margin + i * (card_w + margin) for i in range(cols)]

            # Categorize entities for smart ordering
            # Priority: climate, sensor (temperature), binary_sensor, light, switch, rest
            domain_priority = {
                "climate": 0,
                "sensor": 1,
                "binary_sensor": 2,
                "light": 3,
                "switch": 4,
                "input_boolean": 5,
            }

            sorted_entities = sorted(
                entities,
                key=lambda e: domain_priority.get(self._get_domain(e), 9),
            )

            # Draw entity cards in grid
            row = 0
            col = 0
            max_entities = 18  # 6 rows x 3 cols

            for i, entity in enumerate(sorted_entities[:max_entities]):
                cx = col_x[col]
                cy = y + row * (card_h + 6)

                if cy + card_h > max_y:
                    # Out of space, show count
                    remaining = len(sorted_entities) - i
                    small_font = get_font(12)
                    draw.text(
                        (20, cy),
                        f"  +{remaining} more entities...",
                        fill=MUTED_COLOR,
                        font=small_font,
                    )
                    break

                self._draw_entity_card(draw, cx, cy, card_w, card_h, entity)

                col += 1
                if col >= cols:
                    col = 0
                    row += 1

            # Footer
            draw_footer(draw, f"{len(entities)} entities")
            return img

        except Exception as e:
            logger.error(f"Error rendering home view: {e}")
            img, draw = create_canvas()
            draw_header(draw, "Home", "Error")
            error_font = get_font(20)
            draw_centered_text(draw, "Home display error", 200, error_font, TEXT_COLOR)
            draw_footer(draw, "Error")
            return img

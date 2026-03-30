"""
Finance view for e-ink dashboard.
Displays cryptocurrency prices with 24h change indicators.
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
    draw_progress_bar,
    get_font,
    WIDTH,
    HEIGHT,
    TEXT_COLOR,
    MUTED_COLOR,
    SUCCESS_COLOR,
    HIGHLIGHT_COLOR,
    BG_COLOR,
)

logger = logging.getLogger(__name__)


class FinanceView:
    """Displays cryptocurrency prices and 24h changes."""

    def __init__(self, config=None, service=None):
        self.config = config or {}
        self.service = service

    def _format_price(self, price, currency="usd"):
        """Format price with appropriate precision."""
        if price is None:
            return "N/A"
        if price >= 1000:
            return f"{price:,.2f}"
        elif price >= 1:
            return f"{price:.2f}"
        else:
            return f"{price:.4f}"

    def _format_change(self, change_pct):
        """Format percentage change with sign."""
        if change_pct is None:
            return "N/A", MUTED_COLOR
        sign = "+" if change_pct >= 0 else ""
        color = SUCCESS_COLOR if change_pct >= 0 else HIGHLIGHT_COLOR
        return f"{sign}{change_pct:.2f}%", color

    def render(self):
        """
        Render the finance view.

        Returns:
            PIL.Image - rendered finance screen
        """
        try:
            img, draw = create_canvas()
            now = datetime.now()

            # Header
            currency = self.config.get("finance", {}).get("currency", "usd").upper()
            draw_header(draw, "Finance", f"{currency} {now.strftime('%H:%M')}")

            y = 62
            max_y = HEIGHT - 38

            # Fetch prices
            prices = []
            if self.service:
                try:
                    prices = self.service.get_prices()
                except Exception as e:
                    logger.error(f"Error fetching crypto prices: {e}")

            if not prices:
                msg_font = get_font(24)
                y = draw_centered_text(
                    draw, "No price data", (HEIGHT - 80) // 2, msg_font, MUTED_COLOR
                )
                hint_font = get_font(16)
                draw_centered_text(
                    draw, "Check API connection", y + 15, hint_font, MUTED_COLOR
                )
                draw_footer(draw, "No data")
                return img

            # Draw each coin
            name_font = get_font(20, bold=True)
            symbol_font = get_font(14)
            price_font = get_font(28, bold=True)
            change_font = get_font(16, bold=True)
            detail_font = get_font(12)

            for i, coin in enumerate(prices):
                if y > max_y - 60:
                    remaining = len(prices) - i
                    if remaining > 0:
                        small_font = get_font(14)
                        draw.text(
                            (20, y),
                            f"  +{remaining} more...",
                            fill=MUTED_COLOR,
                            font=small_font,
                        )
                    break

                name = coin.get("name", "Unknown")
                symbol = coin.get("symbol", "???")
                price = coin.get("price", 0)
                change_pct = coin.get("change_pct", 0)
                change_abs = coin.get("change_24h", 0)

                # Name and symbol on left
                draw.text((20, y), name, fill=TEXT_COLOR, font=name_font)
                # Symbol to the right of name
                bbox = draw.textbbox((20, y), name, font=name_font)
                name_end = bbox[2] + 8
                draw.text((name_end, y + 4), symbol, fill=MUTED_COLOR, font=symbol_font)

                # Price (large, right side)
                price_str = self._format_price(price, currency)
                currency_symbol = "$" if currency == "USD" else "€" if currency == "EUR" else "£" if currency == "GBP" else ""
                price_display = f"{currency_symbol}{price_str}"

                bbox = draw.textbbox((0, 0), price_display, font=price_font)
                pw = bbox[2] - bbox[0]
                draw.text((WIDTH - pw - 20, y - 2), price_display, fill=TEXT_COLOR, font=price_font)

                y += 32

                # Change percentage with color
                change_str, change_color = self._format_change(change_pct)
                change_display = f"24h: {change_str}"
                draw.text((35, y), change_display, fill=change_color, font=change_font)

                # Absolute change on right
                if change_abs is not None:
                    sign = "+" if change_abs >= 0 else ""
                    abs_str = f"{sign}{change_abs:.2f}"
                    bbox = draw.textbbox((0, 0), abs_str, font=detail_font)
                    aw = bbox[2] - bbox[0]
                    draw.text((WIDTH - aw - 20, y + 3), abs_str, fill=change_color, font=detail_font)

                y += 24

                # Divider between coins
                if i < len(prices) - 1:
                    draw_divider(draw, y)
                    y += 10

            # Footer
            draw_footer(draw, f"{len(prices)} coins")
            return img

        except Exception as e:
            logger.error(f"Error rendering finance view: {e}")
            img, draw = create_canvas()
            draw_header(draw, "Finance", "Error")
            error_font = get_font(20)
            draw_centered_text(draw, "Finance display error", 200, error_font, TEXT_COLOR)
            draw_footer(draw, "Error")
            return img

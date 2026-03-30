"""
Weather view for e-ink dashboard.
Displays current conditions and 3-day forecast.
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
    SUCCESS_COLOR,
    WARNING_COLOR,
)

logger = logging.getLogger(__name__)


class WeatherView:
    """Displays current weather and forecast."""

    def __init__(self, config=None, service=None):
        self.config = config or {}
        self.service = service

    def render(self):
        """
        Render the weather view.

        Returns:
            PIL.Image - rendered weather screen
        """
        try:
            img, draw = create_canvas()
            now = datetime.now()

            # Header
            draw_header(draw, "Weather", now.strftime("%H:%M"))

            y = 60

            # Fetch data
            current = None
            forecast = []
            if self.service:
                try:
                    current = self.service.get_current()
                except Exception as e:
                    logger.error(f"Error fetching current weather: {e}")
                try:
                    forecast = self.service.get_forecast(days=3)
                except Exception as e:
                    logger.error(f"Error fetching forecast: {e}")

            if not current:
                # No data available
                msg_font = get_font(24)
                y = draw_centered_text(
                    draw, "Weather unavailable", (HEIGHT - 80) // 2, msg_font, MUTED_COLOR
                )
                hint_font = get_font(16)
                draw_centered_text(
                    draw, "Check API key and connection", y + 15, hint_font, MUTED_COLOR
                )
                draw_footer(draw, "No data")
                return img

            # --- Current conditions (top half) ---
            # Large temperature
            temp_font = get_font(56, bold=True)
            temp_str = f"{current['temp']}°"
            y = draw_centered_text(draw, temp_str, y, temp_font, TEXT_COLOR)

            # Description
            desc_font = get_font(22)
            desc = current.get("description", "")
            y = draw_centered_text(draw, desc, y + 4, desc_font, TEXT_COLOR)

            # Details row: feels like, humidity, wind
            detail_font = get_font(14)
            y += 10
            feels_like = current.get("feels_like", "")
            humidity = current.get("humidity", "")
            wind = current.get("wind_speed", "")

            details = f"Feels: {feels_like}°  |  Humidity: {humidity}%  |  Wind: {wind} m/s"
            # Center the details text
            bbox = draw.textbbox((0, 0), details, font=detail_font)
            dw = bbox[2] - bbox[0]
            dx = (WIDTH - dw) // 2
            draw.text((dx, y), details, fill=MUTED_COLOR, font=detail_font)

            # Divider before forecast
            y += 28
            draw_divider(draw, y)
            y += 10

            # --- Forecast (bottom half) ---
            if forecast:
                fc_title_font = get_font(16, bold=True)
                draw.text((20, y), "3-Day Forecast", fill=TEXT_COLOR, font=fc_title_font)
                y += 26

                day_font = get_font(16, bold=True)
                temp_range_font = get_font(16)
                cond_font = get_font(14)

                for day in forecast:
                    if y > HEIGHT - 50:
                        break

                    date_str = day.get("date", "")
                    high = day.get("temp_high", "")
                    low = day.get("temp_low", "")
                    cond = day.get("description", "")

                    # Date on left
                    draw.text((25, y), date_str, fill=TEXT_COLOR, font=day_font)

                    # Temp range centered
                    range_str = f"{high}° / {low}°"
                    bbox = draw.textbbox((0, 0), range_str, font=temp_range_font)
                    rw = bbox[2] - bbox[0]
                    draw.text((350, y), range_str, fill=TEXT_COLOR, font=temp_range_font)

                    # Condition on right
                    if len(cond) > 20:
                        cond = cond[:17] + "..."
                    draw.text((520, y), cond, fill=MUTED_COLOR, font=cond_font)

                    y += 30
            else:
                no_fc_font = get_font(14)
                draw_centered_text(draw, "Forecast unavailable", y + 5, no_fc_font, MUTED_COLOR)

            # Footer
            units = self.config.get("weather", {}).get("units", "metric")
            unit_label = "°C" if units == "metric" else "°F"
            draw_footer(draw, f"Units: {unit_label}")
            return img

        except Exception as e:
            logger.error(f"Error rendering weather view: {e}")
            img, draw = create_canvas()
            draw_header(draw, "Weather", "Error")
            error_font = get_font(20)
            draw_centered_text(draw, "Weather display error", 200, error_font, TEXT_COLOR)
            draw_footer(draw, "Error")
            return img

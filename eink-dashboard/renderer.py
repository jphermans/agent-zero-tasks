"""
Base rendering utilities for e-ink dashboard.
Provides fonts, layout helpers, color palette, and drawing primitives
for the Pimoroni Inky Impression 7.3 inch (800x480, 6-color) display.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

# Display dimensions
WIDTH = 800
HEIGHT = 480

# Inky Impression 7.3 inch color palette
COLORS = {
    "BLACK": (0, 0, 0),
    "WHITE": (255, 255, 255),
    "GREEN": (0, 255, 0),
    "BLUE": (0, 0, 255),
    "RED": (255, 0, 0),
    "YELLOW": (255, 255, 0),
}

# Semantic color aliases
BG_COLOR = COLORS["WHITE"]
TEXT_COLOR = COLORS["BLACK"]
ACCENT_COLOR = COLORS["BLACK"]
HIGHLIGHT_COLOR = COLORS["RED"]
SUCCESS_COLOR = COLORS["GREEN"]
INFO_COLOR = COLORS["BLUE"]
WARNING_COLOR = COLORS["YELLOW"]
MUTED_COLOR = COLORS["BLACK"]


def get_font(size, bold=False):
    """Load a font at the given size."""
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    font_names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "DejaVuSans.ttf",
    ]
    for fname in font_names:
        custom_path = os.path.join(font_dir, fname)
        if os.path.exists(custom_path):
            try:
                return ImageFont.truetype(custom_path, size)
            except Exception:
                continue
    system_paths = [
        "/usr/share/fonts/truetype/dejavu/",
        "/usr/share/fonts/truetype/freefont/",
        "/usr/share/fonts/truetype/liberation/",
        "/usr/share/fonts/truetype/",
    ]
    for sys_dir in system_paths:
        for fname in font_names:
            sys_path = os.path.join(sys_dir, fname)
            if os.path.exists(sys_path):
                try:
                    return ImageFont.truetype(sys_path, size)
                except Exception:
                    continue
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def create_canvas():
    """Create a new blank canvas. Returns (Image, ImageDraw)."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    return img, draw


def draw_header(draw, title, subtitle=""):
    """Draw a standard header bar at the top of the display."""
    draw.rectangle([(0, 0), (WIDTH, 52)], fill=COLORS["BLACK"])
    title_font = get_font(24, bold=True)
    draw.text((15, 12), title, fill=COLORS["WHITE"], font=title_font)
    if subtitle:
        sub_font = get_font(16)
        bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        sw = bbox[2] - bbox[0]
        draw.text((WIDTH - sw - 15, 16), subtitle, fill=COLORS["YELLOW"], font=sub_font)


def draw_footer(draw, text=""):
    """Draw a standard footer bar at the bottom."""
    y = HEIGHT - 28
    draw.rectangle([(0, y), (WIDTH, HEIGHT)], fill=COLORS["BLACK"])
    font = get_font(12)
    if text:
        draw.text((15, y + 6), text, fill=COLORS["WHITE"], font=font)
    nav = "A:Prev  B:Next  C:Refresh  D:Auto"
    bbox = draw.textbbox((0, 0), nav, font=font)
    nw = bbox[2] - bbox[0]
    draw.text((WIDTH - nw - 15, y + 6), nav, fill=COLORS["YELLOW"], font=font)


def draw_centered_text(draw, text, y, font, fill=None, max_width=None):
    """Draw centered text. Returns the y position below the text."""
    if fill is None:
        fill = TEXT_COLOR
    if max_width is None:
        max_width = WIDTH - 40
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (WIDTH - tw) // 2
    if tw > max_width:
        while tw > max_width and len(text) > 3:
            text = text[:-4] + "..."
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            x = (WIDTH - tw) // 2
    draw.text((x, y), text, fill=fill, font=font)
    return y + th


def draw_text_block(draw, text, x, y, font, fill=None, max_width=None, line_spacing=4):
    """Draw a block of wrapped text. Returns y position below."""
    if fill is None:
        fill = TEXT_COLOR
    if max_width is None:
        max_width = WIDTH - x - 20
    avg_char_w = font.getlength("A") if hasattr(font, "getlength") else 10
    chars_per_line = max(10, int(max_width / avg_char_w))
    lines = textwrap.wrap(text, width=chars_per_line)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_h = bbox[3] - bbox[1]
        draw.text((x, y), line, fill=fill, font=font)
        y += line_h + line_spacing
    return y


def draw_progress_bar(draw, x, y, width, height, progress, fill_color=None, bg_color=None):
    """Draw a progress bar (0.0 to 1.0)."""
    if fill_color is None:
        fill_color = SUCCESS_COLOR
    if bg_color is None:
        bg_color = COLORS["BLACK"]
    draw.rectangle([(x, y), (x + width, y + height)], outline=bg_color, width=1)
    fill_w = int(width * min(1.0, max(0.0, progress)))
    if fill_w > 0:
        draw.rectangle([(x + 1, y + 1), (x + fill_w - 1, y + height - 1)], fill=fill_color)


def draw_divider(draw, y, color=None):
    """Draw a horizontal divider line."""
    if color is None:
        color = COLORS["BLACK"]
    draw.line([(20, y), (WIDTH - 20, y)], fill=color, width=1)


def draw_icon_text(draw, icon, text, x, y, font, icon_color=None, text_color=None, spacing=8):
    """Draw an icon character followed by text. Returns y below."""
    if icon_color is None:
        icon_color = ACCENT_COLOR
    if text_color is None:
        text_color = TEXT_COLOR
    draw.text((x, y), icon, fill=icon_color, font=font)
    bbox = draw.textbbox((0, 0), icon, font=font)
    iw = bbox[2] - bbox[0]
    draw.text((x + iw + spacing, y), text, fill=text_color, font=font)
    bbox2 = draw.textbbox((0, 0), text, font=font)
    return y + max(bbox[3] - bbox[1], bbox2[3] - bbox2[1])


def format_temperature(temp, unit="C"):
    """Format temperature for display."""
    if unit.upper() == "F":
        return f"{temp:.0f}F"
    return f"{temp:.0f}C"


def truncate_text(text, max_len=30):
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def view_label(index):
    """Get human-readable view name by index."""
    labels = ["Clock", "Calendar", "Weather", "Tasks", "Email", "Smart Home", "Finance"]
    if 0 <= index < len(labels):
        return labels[index]
    return "Unknown"

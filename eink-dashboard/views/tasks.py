"""
Tasks view for e-ink dashboard.
Displays a task list with checkboxes and priorities from a local JSON file.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
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
    WARNING_COLOR,
    HIGHLIGHT_COLOR,
    BG_COLOR,
)

logger = logging.getLogger(__name__)

PRIORITY_COLORS = {
    "high": HIGHLIGHT_COLOR,
    "medium": WARNING_COLOR,
    "low": MUTED_COLOR,
}


class TasksView:
    """Displays a task list with checkboxes and priorities."""

    def __init__(self, config=None, service=None):
        self.config = config or {}
        tasks_file = config.get("tasks_file", "") if config else ""
        if not tasks_file:
            tasks_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "tasks.json"
            )
        self.tasks_file = tasks_file

    def _load_tasks(self):
        """Load tasks from JSON file."""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
                return data.get("tasks", [])
        except Exception as e:
            logger.error(f"Error loading tasks from {self.tasks_file}: {e}")
        return []

    def render(self):
        """
        Render the tasks view.

        Returns:
            PIL.Image - rendered tasks screen
        """
        try:
            img, draw = create_canvas()
            now = datetime.now()

            # Header
            draw_header(draw, "Tasks", now.strftime("%b %d"))

            y = 60
            max_y = HEIGHT - 38

            tasks = self._load_tasks()

            if not tasks:
                # No tasks
                msg_font = get_font(24)
                y = draw_centered_text(
                    draw, "No tasks", (HEIGHT - 80) // 2, msg_font, MUTED_COLOR
                )
                hint_font = get_font(16)
                draw_centered_text(
                    draw, "Add tasks to tasks.json", y + 15, hint_font, MUTED_COLOR
                )
                draw_footer(draw, "0 tasks")
                return img

            # Summary stats
            total = len(tasks)
            done = sum(1 for t in tasks if t.get("completed", False))
            pending = total - done
            progress = done / total if total > 0 else 0

            # Progress bar
            summary_font = get_font(14)
            summary_text = f"{done}/{total} completed"
            draw.text((20, y), summary_text, fill=TEXT_COLOR, font=summary_font)
            y += 22
            draw_progress_bar(draw, 20, y, WIDTH - 40, 12, progress, SUCCESS_COLOR)
            y += 22

            draw_divider(draw, y)
            y += 8

            # Task list
            task_font = get_font(16)
            small_font = get_font(12)
            max_visible = 10
            shown = 0

            # Sort: pending first (by priority), then completed
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_tasks = sorted(
                tasks,
                key=lambda t: (
                    t.get("completed", False),
                    priority_order.get(t.get("priority", "low"), 2),
                ),
            )

            for task in sorted_tasks:
                if shown >= max_visible or y > max_y - 30:
                    remaining = len(sorted_tasks) - shown
                    if remaining > 0:
                        draw.text(
                            (20, y),
                            f"  +{remaining} more...",
                            fill=MUTED_COLOR,
                            font=small_font,
                        )
                    break

                completed = task.get("completed", False)
                text = task.get("text", task.get("title", "Untitled"))
                priority = task.get("priority", "low")

                # Checkbox
                checkbox = "[x]" if completed else "[ ]"
                check_color = SUCCESS_COLOR if completed else MUTED_COLOR
                draw.text((20, y), checkbox, fill=check_color, font=task_font)

                # Priority indicator
                priority_color = PRIORITY_COLORS.get(priority, MUTED_COLOR)
                draw.rectangle(
                    [(55, y + 2), (59, y + 16)], fill=priority_color
                )

                # Task text
                if completed:
                    # Strikethrough effect: draw text then line through it
                    draw.text((65, y), text, fill=MUTED_COLOR, font=task_font)
                    # Draw strikethrough line
                    bbox = draw.textbbox((65, y), text, font=task_font)
                    mid_y = (bbox[1] + bbox[3]) // 2
                    draw.line(
                        [(65, mid_y), (bbox[2], mid_y)],
                        fill=MUTED_COLOR,
                        width=1,
                    )
                else:
                    # Truncate long text
                    max_chars = 40
                    display_text = text if len(text) <= max_chars else text[:37] + "..."
                    draw.text((65, y), display_text, fill=TEXT_COLOR, font=task_font)

                y += 26
                shown += 1

            # Footer
            draw_footer(draw, f"{pending} pending")
            return img

        except Exception as e:
            logger.error(f"Error rendering tasks view: {e}")
            img, draw = create_canvas()
            draw_header(draw, "Tasks", "Error")
            error_font = get_font(20)
            draw_centered_text(draw, "Failed to load tasks", 200, error_font, TEXT_COLOR)
            draw_footer(draw, "Error")
            return img

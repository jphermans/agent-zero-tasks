"""
E-ink dashboard view layer.
All view classes for rendering dashboard screens on the e-ink display.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from views.clock import ClockView
from views.calendar import CalendarView
from views.weather import WeatherView
from views.tasks import TasksView
from views.email import EmailView
from views.home import HomeView
from views.finance import FinanceView


def get_view_classes():
    """Return a dict mapping view names to their classes."""
    return {
        "clock": ClockView,
        "calendar": CalendarView,
        "weather": WeatherView,
        "tasks": TasksView,
        "email": EmailView,
        "home": HomeView,
        "finance": FinanceView,
    }

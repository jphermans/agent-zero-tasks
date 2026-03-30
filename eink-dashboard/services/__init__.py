# E-ink dashboard service layer.
# Services are imported individually to avoid requiring all optional deps.

def get_service_classes():
    """Return available service classes (only those with deps installed)."""
    services = {}
    try:
        from services.weather import WeatherService
        services["weather"] = WeatherService
    except ImportError:
        pass
    try:
        from services.crypto import CryptoService
        services["crypto"] = CryptoService
    except ImportError:
        pass
    try:
        from services.google_cal import GoogleCalendarService
        services["google_calendar"] = GoogleCalendarService
    except ImportError:
        pass
    try:
        from services.imap_email import EmailService
        services["email"] = EmailService
    except ImportError:
        pass
    try:
        from services.homeassistant import HomeAssistantService
        services["homeassistant"] = HomeAssistantService
    except ImportError:
        pass
    return services

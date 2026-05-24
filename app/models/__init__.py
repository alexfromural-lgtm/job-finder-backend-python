# models package — import all models here so Alembic can discover them
from app.models.user import User, Role  # noqa: F401
from app.models.profiles import JobSeekerProfile, RecruiterProfile  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.application import Application, ApplicationStatus  # noqa: F401
from app.models.saved_job import SavedJob  # noqa: F401
from app.models.notification import Notification, NotificationType  # noqa: F401
from app.models.report import Report, ReportStatus  # noqa: F401

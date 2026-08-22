from app.api.routes.architecture import router as architecture
from app.api.routes.auth import router as auth
from app.api.routes.comparisons import router as comparisons
from app.api.routes.findings import router as findings
from app.api.routes.monitoring import router as monitoring
from app.api.routes.recommendations import router as recommendations
from app.api.routes.reports import router as reports
from app.api.routes.scans import router as scans
from app.api.routes.users import router as users
from app.api.routes.websites import router as websites

__all__ = ["architecture", "auth", "comparisons", "findings", "monitoring",
           "recommendations", "reports", "scans", "users", "websites"]

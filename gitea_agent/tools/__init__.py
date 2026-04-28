from .admin import all_tools as admin_tools
from .issue import all_tools as issue_tools
from .miscellaneous import all_tools as misc_tools
from .notification import all_tools as notification_tools
from .organization import all_tools as org_tools
from .package import all_tools as package_tools
from .repository import all_tools as repo_tools
from .settings import all_tools as settings_tools
from .setup import setup_gitea, show_gitea_config
from .user import all_tools as user_tools

all_tools = [
    setup_gitea,
    show_gitea_config,
    *admin_tools,
    *misc_tools,
    *notification_tools,
    *org_tools,
    *package_tools,
    *issue_tools,
    *repo_tools,
    *settings_tools,
    *user_tools,
]

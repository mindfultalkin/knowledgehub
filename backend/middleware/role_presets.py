# Role presets for middleware

from middleware.role_middleware import require_roles

admin_only = require_roles("ADMIN")
admin_or_master = require_roles("ADMIN", "MASTER")
all_users = require_roles("ADMIN", "MASTER", "STANDARD")

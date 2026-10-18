"""Status, role and ledger type values stored in the database and returned by the API.

The values are persisted and compared by the frontend, so changing one needs a
data migration. Keep this module free of imports so any module can use it.
"""


class Role:
    USER = "user"
    ADMIN = "admin"
    ALL = (USER, ADMIN)


class UserStatus:
    ACTIVE = "active"
    BANNED = "banned"
    ALL = (ACTIVE, BANNED)


class KeyStatus:
    """Stored in api_keys.status."""
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"
    SETTABLE = (ACTIVE, DISABLED)  # what a user may PATCH; deletion goes through keys.soft_delete


class KeyState:
    """Extra values keys.state() derives for a stored ACTIVE key."""
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"
    SUSPENDED = "suspended"


class RedeemStatus:
    UNUSED = "unused"
    USED = "used"
    DISABLED = "disabled"
    ALL = (UNUSED, USED, DISABLED)


class OrderStatus:
    PENDING = "pending"
    PAID = "paid"


class TxType:
    """transactions.type. Usage charges are not written to the ledger."""
    REDEEM = "redeem"
    ONLINE = "online"
    ADMIN = "admin"
    BONUS = "bonus"
    RECHARGE = (REDEEM, ONLINE, ADMIN)  # counted in users.total_recharge_micro

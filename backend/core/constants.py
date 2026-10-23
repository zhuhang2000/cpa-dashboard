"""Status, role and ledger type values stored in the database and returned by the API.

The values are persisted and compared by the frontend, so changing one needs a
data migration. Keep this module free of imports so any module can use it.
"""


class Role:
    """ADMIN runs the whole site; a MANAGER only sees and credits users sharing its tag."""

    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"
    ALL = (USER, ADMIN, MANAGER)
    STAFF = (ADMIN, MANAGER)  # may open the user administration


class UserStatus:
    ACTIVE = "active"
    BANNED = "banned"
    ALL = (ACTIVE, BANNED)


class KeyStatus:
    """Stored in api_keys.status."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"
    SETTABLE = (
        ACTIVE,
        DISABLED,
    )  # what a user may PATCH; deletion goes through api_keys.soft_delete


class KeyState:
    """Extra values api_keys.state() derives for a stored ACTIVE key."""

    EXPIRED = "expired"
    EXHAUSTED = "exhausted"
    SUSPENDED = "suspended"


class RedeemStatus:
    UNUSED = "unused"
    USED = "used"
    DISABLED = "disabled"
    ALL = (UNUSED, USED, DISABLED)


class RedeemType:
    RECHARGE = "recharge"
    GIFT = "gift"
    ALL = (RECHARGE, GIFT)


class OrderStatus:
    PENDING = "pending"
    PAID = "paid"


class TxType:
    """transactions.type. Usage charges are not written to the ledger."""

    REDEEM = "redeem"
    REDEEM_GIFT = "redeem_gift"
    ONLINE = "online"
    ADMIN = "admin"
    BONUS = "bonus"  # an administrator's gift; older rows also hold the retired sign-up bonus
    ALL = (REDEEM, REDEEM_GIFT, ONLINE, ADMIN, BONUS)
    RECHARGE = (REDEEM, ONLINE, ADMIN)  # gifts are excluded from all recharge statistics


VERSION = "1.0.0"
DAY_MS = 86400000

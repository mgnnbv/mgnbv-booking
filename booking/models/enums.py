import enum


class PropertyType(str, enum.Enum):
    APARTMENT = "apartment"     # квартира
    ROOM = "room"                # комната
    NUMBER = "number"            # номер (мини-отель/гостевой дом)
    HOUSE = "house"               # дом


class RentalType(str, enum.Enum):
    SHORT_TERM = "short_term"     # посуточная
    LONG_TERM = "long_term"       # долгосрочная


class BookingStatus(str, enum.Enum):
    PENDING = "pending"           # забронировано, ещё не заехал
    ACTIVE = "active"             # жилец уже проживает
    COMPLETED = "completed"       # выехал, бронь закрыта
    CANCELLED = "cancelled"       # отменена (не блокирует даты)


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"           # ожидается
    PAID = "paid"                 # оплачено
    OVERDUE = "overdue"           # просрочено
    CANCELLED = "cancelled"


class PaymentType(str, enum.Enum):
    RENT = "rent"                 # оплата аренды
    DEPOSIT = "deposit"           # депозит/залог
    UTILITY = "utility"           # коммунальные
    OTHER = "other"

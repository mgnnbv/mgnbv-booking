import enum


class PropertyType(str, enum.Enum):
    APARTMENT = "apartment"
    ROOM = "room"
    NUMBER = "number"
    HOUSE = "house"
    OTHER = "other"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"           
    ACTIVE = "active"             
    COMPLETED = "completed"       
    CANCELLED = "cancelled"       


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"           
    PAID = "paid"                 
    OVERDUE = "overdue"           
    CANCELLED = "cancelled"


class PaymentType(str, enum.Enum):
    RENT = "rent"                 
    DEPOSIT = "deposit"           
    UTILITY = "utility"           
    OTHER = "other"

class PaymentMethod(str, enum.Enum):
    CASH = "cash"                 
    CARD = "card"                 
    TRANSFER = "transfer"         
    OTHER = "other"
    
    
def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]
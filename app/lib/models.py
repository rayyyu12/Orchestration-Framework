from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import uuid
import time


class OrderStatus(str, Enum):
    """Enumeration of possible order statuses"""
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    INVENTORY_CHECKED = "INVENTORY_CHECKED"
    PAYMENT_PROCESSED = "PAYMENT_PROCESSED"
    FULFILLED = "FULFILLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PaymentStatus(str, Enum):
    """Enumeration of possible payment statuses"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OrderItem(BaseModel):
    """Model representing an item in an order"""
    product_id: str
    quantity: int
    unit_price: float
    
    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v
    
    @validator('unit_price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v


class CustomerInfo(BaseModel):
    """Model representing customer information"""
    customer_id: str
    email: str
    name: str


class PaymentInfo(BaseModel):
    """Model representing payment information"""
    payment_method: str
    transaction_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Optional[float] = None


class Order(BaseModel):
    """Model representing an order"""
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer: CustomerInfo
    items: List[OrderItem]
    shipping_address: Dict[str, str]
    status: OrderStatus = OrderStatus.RECEIVED
    payment: PaymentInfo
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    total_amount: Optional[float] = None
    notes: Optional[str] = None
    expiration_time: int = Field(
        default_factory=lambda: int(time.time() + 7 * 24 * 60 * 60)  # 7 days TTL
    )
    
    def calculate_total(self) -> float:
        """Calculate the total order amount"""
        return sum(item.quantity * item.unit_price for item in self.items)
    
    def to_dynamo_dict(self) -> Dict[str, Any]:
        """Convert order to DynamoDB item format"""
        return {
            "order_id": self.order_id,
            "created_at": self.created_at,
            "customer": self.customer.dict(),
            "items": [item.dict() for item in self.items],
            "shipping_address": self.shipping_address,
            "status": self.status,
            "payment": self.payment.dict(),
            "updated_at": self.updated_at,
            "total_amount": self.total_amount or self.calculate_total(),
            "notes": self.notes,
            "expiration_time": self.expiration_time
        }
    
    @classmethod
    def from_dynamo_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Create an Order instance from DynamoDB item"""
        # Convert DynamoDB nested maps to model objects
        data["customer"] = CustomerInfo(**data["customer"])
        data["items"] = [OrderItem(**item) for item in data["items"]]
        data["payment"] = PaymentInfo(**data["payment"])
        
        return cls(**data)


class InventoryItem(BaseModel):
    """Model representing an inventory item"""
    product_id: str
    name: str
    description: str
    price: float
    stock_quantity: int
    
    def to_dynamo_dict(self) -> Dict[str, Any]:
        """Convert inventory item to DynamoDB item format"""
        return self.dict()
    
    @classmethod
    def from_dynamo_dict(cls, data: Dict[str, Any]) -> 'InventoryItem':
        """Create an InventoryItem instance from DynamoDB item"""
        return cls(**data)
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean
from src.database import Base


class ShopSettings(Base):
    __tablename__ = "shop_settings"

    id = Column(Integer, primary_key=True, default=1)
    shop_name = Column(String(255), default="ParfumShop")
    min_order_amount = Column(Numeric(10, 2), default=0)
    payment_info_text = Column(Text, nullable=True)
    contacts_text = Column(Text, nullable=True)
    shop_phone = Column(String(50), nullable=True)
    shop_email = Column(String(255), nullable=True)
    about_text = Column(Text, nullable=True)
    show_out_of_stock = Column(Boolean, default=False, server_default="0")

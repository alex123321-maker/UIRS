from sqlalchemy.orm import relationship
from src.core import security
from src.models.rwmodel import RWModel as Base
from sqlalchemy import Column, Integer, String



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    salt = Column(String(255), nullable=False)
    hashed_password = Column(String(256), nullable=True)
    recipes = relationship("Recipe", back_populates="author")
    def check_password(self, password: str) -> bool:
        return security.verify_password(self.salt + password, self.hashed_password)

    def change_password(self, password: str) -> None:
        self.salt = security.generate_salt()
        self.hashed_password = security.get_password_hash(self.salt + password)

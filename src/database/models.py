import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from .db import Base


class Role(enum.Enum):
    admin: str = "admin"
    user: str = "user"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    avatar_url = Column(String, nullable=True)
    roles = Column(Enum(Role), default=Role.user)
    contacts = relationship("Contact", back_populates="user")

    def to_dict(self):
        """
        Convert the User object to a dictionary representation.

        Returns:
            dict: A dictionary containing the user's id, email, verification status,
                  avatar URL, and roles.
        """

        return {
            "id": self.id,
            "email": self.email,
            "is_verified": self.is_verified,
            "avatar_url": self.avatar_url,
            "roles": self.roles.value,
        }


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, index=True, nullable=False)
    phone_number = Column(String, nullable=False)
    birthday = Column(Date, nullable=False)
    additional_data = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="contacts")

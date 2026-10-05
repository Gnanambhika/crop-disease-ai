from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


class AuthRateLimit(Base):
    __tablename__ = 'auth_rate_limits'
    bucket_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)

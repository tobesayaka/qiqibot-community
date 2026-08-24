from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class QA(Base):
    __tablename__ = "qa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    @property
    def image_list(self) -> list[str]:
        if not self.images:
            return []
        return json.loads(self.images)

    @image_list.setter
    def image_list(self, value: list[str]):
        self.images = json.dumps(value, ensure_ascii=False) if value else None

    def format_short(self) -> str:
        q = self.question[:30] + ("..." if len(self.question) > 30 else "")
        return f"#{self.id} | {q}"

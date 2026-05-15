from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid

class SourceImage(Base):
    __tablename__ = "source_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"))
    file_path = Column(String)
    filename = Column(String)
    width = Column(Integer)
    height = Column(Integer)

    project = relationship("Project", back_populates="source_images")
    page = relationship("DocumentPage", back_populates="source_image", uselist=False)

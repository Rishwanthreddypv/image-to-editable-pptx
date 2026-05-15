from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid

class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"))
    source_image_id = Column(String, ForeignKey("source_images.id"))
    page_number = Column(Integer, default=1)

    project = relationship("Project", back_populates="pages")
    source_image = relationship("SourceImage", back_populates="page")
    layers = relationship("DocumentLayer", back_populates="page", cascade="all, delete-orphan")

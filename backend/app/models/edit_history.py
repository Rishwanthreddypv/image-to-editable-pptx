from sqlalchemy import Column, String, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid

class DocumentLayer(Base):
    __tablename__ = "document_layers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    page_id = Column(String, ForeignKey("document_pages.id"))
    type = Column(String) # text, table, figure, image
    
    # Geometry
    x = Column(Float)
    y = Column(Float)
    width = Column(Float)
    height = Column(Float)
    
    content = Column(JSON) # Detailed layer content

    page = relationship("DocumentPage", back_populates="layers")

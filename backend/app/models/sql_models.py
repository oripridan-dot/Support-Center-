from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class Brand(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    primary_color: Optional[str] = "#000000"
    secondary_color: Optional[str] = "#ffffff"
    
    product_families: List["ProductFamily"] = Relationship(back_populates="brand")
    documents: List["Document"] = Relationship(back_populates="brand")
    media: List["Media"] = Relationship(back_populates="brand")

class ProductFamily(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    brand_id: int = Field(foreign_key="brand.id")
    
    brand: Brand = Relationship(back_populates="product_families")
    products: List["Product"] = Relationship(back_populates="family")

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    image_url: Optional[str] = None
    family_id: int = Field(foreign_key="productfamily.id")
    
    family: ProductFamily = Relationship(back_populates="products")
    documents: List["Document"] = Relationship(back_populates="product")
    media: List["Media"] = Relationship(back_populates="product")

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: str
    content: Optional[str] = None  # Full text content for vectorization
    content_hash: Optional[str] = None
    doc_type: Optional[str] = "manual"  # "manual", "datasheet", "guide", etc.
    file_path: Optional[str] = None  # Local file path if downloaded
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    brand_id: int = Field(foreign_key="brand.id")
    product_id: Optional[int] = Field(default=None, foreign_key="product.id")
    
    brand: Brand = Relationship(back_populates="documents")
    product: Optional[Product] = Relationship(back_populates="documents")
    media: List["Media"] = Relationship(back_populates="document")

class Media(SQLModel, table=True):
    """Official media (images, PDFs, logos) attached to documents and brands."""
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)
    media_type: str = Field(index=True)  # "logo", "screenshot", "diagram", "manual", "spec_sheet"
    alt_text: Optional[str] = None
    brand_id: int = Field(foreign_key="brand.id", index=True)
    product_id: Optional[int] = Field(default=None, foreign_key="product.id", index=True)
    document_id: Optional[int] = Field(default=None, foreign_key="document.id")
    relevance_score: float = 1.0  # 0-1, where 1 = highly relevant
    last_verified: datetime = Field(default_factory=datetime.utcnow)
    is_official: bool = True  # Ensure only official sources
    
    brand: "Brand" = Relationship()
    product: Optional["Product"] = Relationship()
    document: Optional["Document"] = Relationship(back_populates="media")

class IngestLog(SQLModel, table=True):
    """Track ingestion history and performance."""
    id: Optional[int] = Field(default=None, primary_key=True)
    brand_id: int = Field(foreign_key="brand.id", index=True)
    url: str
    status: str = Field(index=True)  # "success", "failed", "skipped", "duplicate"
    reason: Optional[str] = None
    documents_created: int = 0
    media_attached: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    ingestion_time_ms: int = 0
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from ..core.database import get_session
from ..models.sql_models import Brand, Product, ProductFamily, Document
from ..models.ingestion_status import IngestionStatus

router = APIRouter()

class BrandWithStats(BaseModel):
    id: int
    name: str
    logo_url: Optional[str] = None
    website_url: str
    description: Optional[str] = None
    primary_color: Optional[str] = "#000000"
    secondary_color: Optional[str] = "#ffffff"
    total_products: int
    covered_products: int
    coverage_percentage: float
    last_ingestion: Optional[datetime] = None
    # Real data fields
    total_documents: int
    target_documents: int
    document_coverage_percentage: float

@router.post("", response_model=Brand)
def create_brand(brand: Brand, session: Session = Depends(get_session)):
    session.add(brand)
    session.commit()
    session.refresh(brand)
    return brand

@router.get("/stats", response_model=List[BrandWithStats])
def read_brands_stats(session: Session = Depends(get_session)):
    brands = session.exec(select(Brand)).all()
    stats = []
    
    # Pre-fetch ingestion statuses
    ingestion_statuses = session.exec(select(IngestionStatus)).all()
    status_map = {s.brand_id: s for s in ingestion_statuses}
    
    for brand in brands:
        # Get real counts
        total_docs = session.exec(select(func.count(Document.id)).where(Document.brand_id == brand.id)).one()
        
        # Calculate coverage
        # If we have ingestion status with discovered URLs, use that as target
        # Otherwise, use total_docs as target (assuming complete) or 0 if empty
        target = 0
        status = status_map.get(brand.id)
        
        if status and status.urls_discovered > 0:
            target = status.urls_discovered
        elif total_docs > 0:
            target = total_docs
            
        # Ensure target is at least total_docs
        if target < total_docs:
            target = total_docs
            
        # If still 0, we don't know
        if target == 0:
            target = 1 # Avoid division by zero, show 0%
            
        coverage = (total_docs / target) * 100 if target > 0 else 0
        
        # 1. Total products
        total_products = session.exec(
            select(func.count(Product.id))
            .join(ProductFamily)
            .where(ProductFamily.brand_id == brand.id)
        ).one()
        
        # 2. Covered products
        covered_products = session.exec(
            select(func.count(func.distinct(Product.id)))
            .join(ProductFamily)
            .join(Document, Product.id == Document.product_id)
            .where(ProductFamily.brand_id == brand.id)
        ).one()
        
        # 3. Total documents (real data!)
        total_documents = session.exec(
            select(func.count(Document.id))
            .where(Document.brand_id == brand.id)
        ).one()
        
        # 4. Last ingestion
        last_ingestion = session.exec(
            select(func.max(Document.last_updated))
            .where(Document.brand_id == brand.id)
        ).one()
        
        # Product-based coverage (legacy, might be 0 if no products)
        coverage_percentage = (covered_products / total_products * 100) if total_products > 0 else 0.0
        
        # Document-based coverage (REAL DATA)
        target_docs = target
        document_coverage = (total_documents / target_docs * 100) if target_docs > 0 else 0.0
        
        stats.append(BrandWithStats(
            id=brand.id,
            name=brand.name,
            logo_url=brand.logo_url,
            website_url=brand.website_url,
            description=brand.description,
            primary_color=brand.primary_color,
            secondary_color=brand.secondary_color,
            total_products=total_products,
            covered_products=covered_products,
            coverage_percentage=round(coverage_percentage, 1),
            last_ingestion=last_ingestion,
            total_documents=total_documents,
            target_documents=target_docs,
            document_coverage_percentage=min(round(document_coverage, 1), 100.0)
        ))
    
    # Sort by document coverage (real data!)
    stats.sort(key=lambda x: (x.document_coverage_percentage, x.last_ingestion or datetime.min), reverse=True)
    
    return stats

@router.get("", response_model=List[Brand])
def read_brands(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    brands = session.exec(select(Brand).offset(skip).limit(limit)).all()
    return brands

@router.get("/{brand_id}/products", response_model=List[Product])
def read_brand_products(brand_id: int, session: Session = Depends(get_session)):
    # Get all products belonging to families of this brand
    products = session.exec(
        select(Product)
        .join(ProductFamily)
        .where(ProductFamily.brand_id == brand_id)
    ).all()
    return products

@router.get("/{brand_id}", response_model=BrandWithStats)
def read_brand(brand_id: int, session: Session = Depends(get_session)):
    brand = session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # 1. Total products
    total_products = session.exec(
        select(func.count(Product.id))
        .join(ProductFamily)
        .where(ProductFamily.brand_id == brand_id)
    ).one()
    
    # 2. Covered products (products with at least one document)
    covered_products = session.exec(
        select(func.count(func.distinct(Product.id)))
        .join(ProductFamily)
        .join(Document, Product.id == Document.product_id)
        .where(ProductFamily.brand_id == brand_id)
    ).one()
    
    # 3. Total documents (REAL DATA!)
    total_documents = session.exec(
        select(func.count(Document.id))
        .where(Document.brand_id == brand_id)
    ).one()
    
    # 4. Last ingestion
    last_ingestion = session.exec(
        select(func.max(Document.last_updated))
        .where(Document.brand_id == brand_id)
    ).one()
    
    # Product-based coverage (legacy)
    coverage_percentage = (covered_products / total_products * 100) if total_products > 0 else 0.0
    
    # Document-based coverage (REAL DATA)
    # Get ingestion status for dynamic target
    status = session.exec(select(IngestionStatus).where(IngestionStatus.brand_id == brand_id)).first()
    
    target_docs = 0
    if status and status.urls_discovered > 0:
        target_docs = status.urls_discovered
    elif total_documents > 0:
        target_docs = total_documents
        
    if target_docs < total_documents:
        target_docs = total_documents
        
    if target_docs == 0:
        target_docs = 1
        
    document_coverage = (total_documents / target_docs * 100) if target_docs > 0 else 0.0
    
    return BrandWithStats(
        id=brand.id,
        name=brand.name,
        logo_url=brand.logo_url,
        website_url=brand.website_url,
        description=brand.description,
        primary_color=brand.primary_color,
        secondary_color=brand.secondary_color,
        total_products=total_products,
        covered_products=covered_products,
        coverage_percentage=round(coverage_percentage, 1),
        last_ingestion=last_ingestion,
        total_documents=total_documents,
        target_documents=target_docs,
        document_coverage_percentage=min(round(document_coverage, 1), 100.0)
    )

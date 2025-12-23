from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from ..core.database import get_session
from ..models.sql_models import Brand, Product, ProductFamily, Document

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
    for brand in brands:
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
        
        # 3. Last ingestion
        last_ingestion = session.exec(
            select(func.max(Document.last_updated))
            .where(Document.brand_id == brand.id)
        ).one()
        
        coverage_percentage = (covered_products / total_products * 100) if total_products > 0 else 0.0
        
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
            last_ingestion=last_ingestion
        ))
    
    # Sort by coverage percentage (descending) and then by last ingestion (descending)
    stats.sort(key=lambda x: (x.coverage_percentage, x.last_ingestion or datetime.min), reverse=True)
    
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
    
    # Calculate stats
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
    
    coverage_percentage = (covered_products / total_products * 100) if total_products > 0 else 0.0
    
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
        coverage_percentage=round(coverage_percentage, 1)
    )

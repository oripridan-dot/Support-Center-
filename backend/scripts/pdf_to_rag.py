"""
PDF Text Extraction and ChromaDB Indexing
Extracts text from downloaded brand documentation PDFs and indexes them in the RAG system

Usage:
    python scripts/pdf_to_rag.py [brand_name]
    
Examples:
    python scripts/pdf_to_rag.py "Adam Audio"
    python scripts/pdf_to_rag.py  # Process all brands
"""

import sys
import os
import json
from pathlib import Path
import logging
import hashlib
from datetime import datetime
import asyncio

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pdfplumber
from app.services.rag_service import ingest_document
from app.core.database import Session, engine
from app.models.sql_models import Brand, Product, ProductFamily, Document
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

BRAND_DOCS_DIR = Path("data/brand_docs")

class PDFToRAGProcessor:
    def __init__(self, brand_name=None):
        self.brand_name = brand_name
        self.processed_count = 0
        self.error_count = 0
        
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                full_text = "\n\n".join(text_parts)
                return full_text.strip()
        except Exception as e:
            logging.error(f"Error extracting text from {pdf_path}: {e}")
            return None
    
    def get_or_create_brand(self, session, brand_name):
        """Get brand from DB or create if doesn't exist"""
        # Try to find existing brand (case-insensitive)
        statement = select(Brand).where(Brand.name.ilike(brand_name))
        brand = session.exec(statement).first()
        
        if not brand:
            # Create new brand
            brand = Brand(
                name=brand_name,
                website_url=f"https://www.{brand_name.lower().replace(' ', '-')}.com"
            )
            session.add(brand)
            session.commit()
            session.refresh(brand)
            logging.info(f"Created new brand: {brand_name}")
        
        return brand
    
    def get_or_create_product(self, session, brand_id, product_name):
        """Get product from DB or create if doesn't exist"""
        # First check if product exists
        statement = select(Product).join(ProductFamily).where(
            Product.name.ilike(product_name),
            ProductFamily.brand_id == brand_id
        )
        product = session.exec(statement).first()
        
        if not product:
            # Get or create default product family
            family_statement = select(ProductFamily).where(
                ProductFamily.brand_id == brand_id,
                ProductFamily.name == "General"
            )
            family = session.exec(family_statement).first()
            
            if not family:
                family = ProductFamily(
                    name="General",
                    brand_id=brand_id
                )
                session.add(family)
                session.commit()
                session.refresh(family)
            
            # Create product
            product = Product(
                name=product_name,
                family_id=family.id
            )
            session.add(product)
            session.commit()
            session.refresh(product)
            logging.info(f"Created new product: {product_name}")
        
        return product
    
    async def process_pdf(self, pdf_path, manifest_entry):
        """Process a single PDF: extract text and index in RAG"""
        logging.info(f"Processing: {pdf_path.name}")
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            logging.warning(f"  ⚠️ Insufficient text extracted ({len(text) if text else 0} chars)")
            self.error_count += 1
            return False
        
        try:
            with Session(engine) as session:
                # Get or create brand
                brand = self.get_or_create_brand(session, self.brand_name)
                
                # Get or create product
                product_name = manifest_entry.get('product_name', 'Unknown')
                product = self.get_or_create_product(session, brand.id, product_name)
                
                # Check if document already exists
                content_hash = hashlib.md5(text.encode()).hexdigest()
                doc_statement = select(Document).where(
                    Document.url == manifest_entry['url'],
                    Document.brand_id == brand.id
                )
                existing_doc = session.exec(doc_statement).first()
                
                if existing_doc:
                    if existing_doc.content_hash == content_hash:
                        logging.info(f"  ⏭️ Already indexed (unchanged)")
                        return True
                    else:
                        logging.info(f"  🔄 Updating existing document")
                
                # Create document title
                doc_type = manifest_entry.get('doc_type', 'other')
                title = f"{product_name} - {doc_type.replace('_', ' ').title()}"
                
                # Create or update document record
                if existing_doc:
                    existing_doc.content_hash = content_hash
                    existing_doc.last_updated = datetime.utcnow()
                    session.add(existing_doc)
                else:
                    doc = Document(
                        title=title,
                        url=manifest_entry['url'],
                        content_hash=content_hash,
                        last_updated=datetime.utcnow(),
                        brand_id=brand.id,
                        product_id=product.id
                    )
                    session.add(doc)
                
                session.commit()
                
                # Ingest into RAG (ChromaDB)
                metadata = {
                    "brand": self.brand_name,
                    "product": product_name,
                    "doc_type": doc_type,
                    "source_url": manifest_entry['url'],
                    "title": title
                }
                
                await ingest_document(text=text, metadata=metadata)
                
                logging.info(f"  ✅ Indexed: {len(text)} chars")
                self.processed_count += 1
                return True
                
        except Exception as e:
            logging.error(f"  ✗ Error processing: {e}")
            self.error_count += 1
            return False
    
    async def process_brand(self, brand_name):
        """Process all PDFs for a brand"""
        self.brand_name = brand_name
        brand_dir = BRAND_DOCS_DIR / brand_name.lower().replace(' ', '_')
        
        if not brand_dir.exists():
            logging.error(f"Brand directory not found: {brand_dir}")
            return
        
        # Load manifest
        manifest_path = brand_dir / "download_manifest.json"
        if not manifest_path.exists():
            logging.error(f"Manifest not found: {manifest_path}")
            return
        
        manifest = json.loads(manifest_path.read_text())
        logging.info(f"\n{'='*80}")
        logging.info(f"Processing {brand_name}: {len(manifest)} PDFs")
        logging.info(f"{'='*80}\n")
        
        for entry in manifest:
            pdf_path = Path(entry['filepath'])
            if pdf_path.exists():
                await self.process_pdf(pdf_path, entry)
            else:
                logging.warning(f"PDF not found: {pdf_path}")
        
        # Summary
        logging.info(f"\n{'='*80}")
        logging.info(f"PROCESSING COMPLETE: {brand_name}")
        logging.info(f"{'='*80}")
        logging.info(f"Successfully processed: {self.processed_count}")
        logging.info(f"Errors: {self.error_count}")
        logging.info(f"{'='*80}\n")
    
    async def process_all_brands(self):
        """Process all brands in the brand_docs directory"""
        if not BRAND_DOCS_DIR.exists():
            logging.error(f"Brand docs directory not found: {BRAND_DOCS_DIR}")
            return
        
        brand_dirs = [d for d in BRAND_DOCS_DIR.iterdir() if d.is_dir()]
        logging.info(f"Found {len(brand_dirs)} brand directories")
        
        for brand_dir in brand_dirs:
            # Convert directory name back to brand name
            brand_name = brand_dir.name.replace('_', ' ').title()
            await self.process_brand(brand_name)


async def main():
    processor = PDFToRAGProcessor()
    
    if len(sys.argv) > 1:
        # Process specific brand
        brand_name = sys.argv[1]
        await processor.process_brand(brand_name)
    else:
        # Process all brands
        await processor.process_all_brands()


if __name__ == "__main__":
    asyncio.run(main())

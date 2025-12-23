"""
Enhanced RAG Service with Media Attachment
Returns official documents, images, and brand logos with every response
"""

import logging
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from app.core.database import engine
from app.models.sql_models import Brand, Document, Media
from app.services.rag_service import ask_question

logger = logging.getLogger(__name__)


async def get_brand_logo(brand_id: int) -> Optional[str]:
    """Get official brand logo URL"""
    try:
        with Session(engine) as session:
            brand = session.get(Brand, brand_id)
            if brand:
                return brand.logo_url
    except Exception as e:
        logger.warning(f"Error fetching brand logo: {e}")
    return None


async def get_relevant_media(
    context_docs: List[str],
    brand_id: int,
    question: str,
    product_id: Optional[int] = None,
    limit: int = 10
) -> List[Media]:
    """Get official media relevant to the query"""
    try:
        with Session(engine) as session:
            # Query media related to documents in context
            query = select(Media).where(
                Media.brand_id == brand_id,
                Media.is_official == True
            )
            
            # Prioritize product-specific media if querying about a product
            if product_id:
                query = query.where(
                    (Media.product_id == product_id) |
                    (Media.product_id == None)  # Include brand-level media too
                )
            
            media_list = session.exec(query).all()
            
            # Sort by relevance score
            media_list = sorted(
                media_list,
                key=lambda m: m.relevance_score,
                reverse=True
            )[:limit]
            
            return media_list
    except Exception as e:
        logger.warning(f"Error fetching relevant media: {e}")
        return []


async def ask_question_with_media(
    question: str,
    brand_id: int = None,
    product_id: int = None,
    is_first_message: bool = False,
    history: list = [],
    include_media: bool = True
) -> Dict[str, Any]:
    """
    Enhanced ask_question that includes official media attachment
    
    Returns:
    {
        "answer": "...",
        "sources": [...],
        "media": {
            "brand_logo": "...",
            "relevant_documents": [...],
            "images": [...],
            "manuals": [...]
        }
    }
    """
    
    # Get the base answer from original RAG
    answer = await ask_question(
        question=question,
        brand_id=brand_id,
        is_first_message=is_first_message,
        history=history,
        product_id=product_id
    )
    
    # Enhanced response with media
    response = {
        "answer": answer,
        "sources": [],
        "media": {
            "brand_logo": None,
            "relevant_documents": [],
            "images": [],
            "manuals": [],
            "specifications": []
        }
    }
    
    if not include_media or not brand_id:
        return response
    
    # Get brand logo
    response["media"]["brand_logo"] = await get_brand_logo(brand_id)
    
    # Get relevant media
    relevant_media = await get_relevant_media(
        context_docs=[],  # Would be populated from context in real usage
        brand_id=brand_id,
        question=question,
        product_id=product_id
    )
    
    # Categorize media by type
    media_by_type = {}
    for media in relevant_media:
        if media.media_type not in media_by_type:
            media_by_type[media.media_type] = []
        media_by_type[media.media_type].append(media.url)
    
    # Populate response media
    response["media"]["relevant_documents"] = media_by_type.get("manual", [])[:3]
    response["media"]["images"] = media_by_type.get("screenshot", [])[:5]
    response["media"]["manuals"] = media_by_type.get("manual", [])[:5]
    response["media"]["specifications"] = media_by_type.get("spec_sheet", [])[:3]
    
    # Remove empty sections
    response["media"] = {
        k: v for k, v in response["media"].items()
        if v or k == "brand_logo"
    }
    
    return response


async def index_media_from_document(
    document: Document,
    content_html: str,
    brand_id: int
) -> int:
    """
    Extract and index media from a document
    Returns count of media items indexed
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    
    media_count = 0
    
    try:
        soup = BeautifulSoup(content_html, 'html.parser')
        
        with Session(engine) as session:
            # Extract images
            for img in soup.find_all('img'):
                img_src = img.get('src')
                if not img_src:
                    continue
                
                # Make absolute URL
                img_url = urljoin(document.url, img_src)
                
                # Skip common UI elements
                alt_text = img.get('alt', '')
                if any(skip in alt_text.lower() for skip in ['logo', 'icon', 'menu']):
                    continue
                
                # Check if already exists
                existing = session.exec(
                    select(Media).where(Media.url == img_url)
                ).first()
                
                if not existing:
                    media = Media(
                        url=img_url,
                        media_type="screenshot",
                        alt_text=alt_text,
                        brand_id=brand_id,
                        document_id=document.id,
                        relevance_score=0.8,
                        is_official=True
                    )
                    session.add(media)
                    media_count += 1
            
            # Extract PDFs and manuals from links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if not href:
                    continue
                
                # Check for PDFs and manuals
                if any(ext in href.lower() for ext in ['.pdf', 'manual', 'guide', 'datasheet']):
                    doc_url = urljoin(document.url, href)
                    
                    # Check if already exists
                    existing = session.exec(
                        select(Media).where(Media.url == doc_url)
                    ).first()
                    
                    if not existing:
                        link_text = link.get_text().strip()
                        media_type = "manual" if "manual" in link_text.lower() else "spec_sheet"
                        
                        media = Media(
                            url=doc_url,
                            media_type=media_type,
                            alt_text=link_text,
                            brand_id=brand_id,
                            document_id=document.id,
                            relevance_score=0.9,
                            is_official=True
                        )
                        session.add(media)
                        media_count += 1
            
            if media_count > 0:
                session.commit()
                logger.info(f"Indexed {media_count} media items from {document.url}")
    
    except Exception as e:
        logger.warning(f"Error indexing media from {document.url}: {e}")
    
    return media_count

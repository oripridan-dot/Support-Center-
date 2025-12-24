import os
from ..core.vector_db import get_collection
from ..core.config import settings
from .prompt_manager import prompt_manager
from ..core.database import get_session
from ..models.sql_models import Product, ProductFamily, Brand
from sqlmodel import select
import uuid
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Initialize LangChain components
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=settings.GEMINI_API_KEY)
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", google_api_key=settings.GEMINI_API_KEY)

collection = get_collection()

async def ingest_document(text: str, metadata: dict):
    """
    Split text into chunks and store in vector DB.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len,
    )
    
    chunks = text_splitter.split_text(text)
    
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [metadata for _ in chunks]
    
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    return len(chunks)

def extract_product_model(question: str) -> str:
    """
    Extract product model name from question.
    Matches patterns like T5V, A7V, T10S, etc.
    """
    import re
    # Match patterns: letter(s) + number(s) + optional letter(s)
    match = re.search(r'\b([A-Z]+\d+[A-Z]*)\b', question.upper())
    if match:
        return match.group(1)
    return None

async def ask_question(question: str, brand_id: int = None, is_first_message: bool = False, history: list[dict] = [], product_id: int = None):
    """
    Retrieve context and generate answer using Gemini.
    """
    # 1. Query Vector DB
    # Detect if the user is asking for a comparison or general brand info
    is_comparison = any(keyword in question.lower() for keyword in ["vs", "difference", "compare", "better", "between"])
    
    # Try to extract product model from question
    product_model = extract_product_model(question)
    print(f"[RAG DEBUG] Question: {question}")
    print(f"[RAG DEBUG] Extracted product model: {product_model}")
    print(f"[RAG DEBUG] Brand ID: {brand_id}")
    
    query_params = {
        "query_texts": [question],
        "n_results": 15  # Increased from 10 to get more context
    }
    
    where_clause = {}
    
    # If we found a product model in the question, prioritize that
    if product_model and not is_comparison:
        # First try: query with product model filter (using brand metadata, not brand_id)
        session = next(get_session())
        if brand_id:
            statement = select(Brand).where(Brand.id == brand_id)
            brand = session.exec(statement).first()
            if brand:
                where_clause["brand"] = brand.name
                # Note: We'll do a post-filter for product name since ChromaDB doesn't support partial matching well
    elif brand_id:
        # Use brand name from database
        session = next(get_session())
        statement = select(Brand).where(Brand.id == brand_id)
        brand = session.exec(statement).first()
        if brand:
            where_clause["brand"] = brand.name
    
    # Only filter by product_id if it's NOT a comparison question
    if product_id and not is_comparison:
        where_clause["product_id"] = product_id
        
    if where_clause:
        if len(where_clause) > 1:
            query_params["where"] = {"$and": [{k: v} for k, v in where_clause.items()]}
        else:
            query_params["where"] = where_clause
        
    # Check if collection has documents to avoid ChromaDB errors on empty collections
    try:
        count = collection.count()
    except Exception as e:
        print(f"Error accessing ChromaDB: {e}")
        count = 0

    if count == 0:
        context_text = "No documentation available yet."
        context_docs = []
        results = {'metadatas': [[]]}
    else:
        try:
            # Use a more robust query approach
            results = collection.query(**query_params)
            context_docs = results['documents'][0] if results['documents'] else []
            context_metas = results['metadatas'][0] if results['metadatas'] else []
            
            # If we extracted a product model, prioritize docs matching that model
            if product_model and context_docs:
                # Sort results: matching product first
                combined = list(zip(context_docs, context_metas))
                combined.sort(key=lambda x: product_model.lower() not in x[1].get('product', '').lower())
                context_docs = [doc for doc, _ in combined]
                context_metas = [meta for _, meta in combined]
                results['documents'][0] = context_docs
                results['metadatas'][0] = context_metas
            
            context_text = "\n\n".join([f"--- Context {i+1} ---\n{doc}" for i, doc in enumerate(context_docs)])
        except Exception as e:
            print(f"CRITICAL: ChromaDB query failed: {e}")
            # If it's an internal error, the index might be corrupted.
            # We return a friendly message instead of crashing.
            context_text = "I'm currently having trouble accessing the technical manuals, but I can still help you based on my general knowledge of these products."
            context_docs = []
            results = {'metadatas': [[]]}
    
    # Check for list_products intent and fetch from SQL if needed
    intent = prompt_manager.determine_intent(question)
    if intent == "list_products" and brand_id:
        try:
            session = next(get_session())
            statement = select(Product).join(ProductFamily).where(ProductFamily.brand_id == brand_id)
            products = session.exec(statement).all()
            
            if products:
                product_list_text = "### AVAILABLE PRODUCTS (from database):\n"
                for p in products:
                    product_list_text += f"- {p.name}\n"
                
                context_text = product_list_text + "\n\n" + context_text
        except Exception as e:
            print(f"Error fetching products from SQL: {e}")

    # 2. Generate Answer with Gemini
    greeting_instruction = "Start with a simple one-sentence greeting. Avoid long introductions." if is_first_message else "Do NOT include a greeting. Start directly with the answer."
    
    # Format history
    history_text = ""
    if history:
        history_text = "### CONVERSATION HISTORY:\n"
        for msg in history[-10:]: # Keep last 10
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role}: {msg.get('content')}\n"
        history_text += "\n"

    # Determine intent and get template
    template = prompt_manager.get_template(intent)
    
    # Fill template
    prompt = template.format(
        context=context_text,
        question=question,
        history=history_text
    )
    
    # Add greeting instruction if needed (can be appended or part of template logic, 
    # but for now we append it as a system note if it's not in the template)
    if is_first_message:
        prompt += "\n\nNOTE: Start with a simple one-sentence greeting."
    else:
        prompt += "\n\nNOTE: Do NOT include a greeting. Start directly with the answer."

    response = await llm.ainvoke(prompt)
    
    answer = response.content
    if isinstance(answer, list):
        answer = "\n".join([item.get("text", "") if isinstance(item, dict) else str(item) for item in answer])
    
    # Extract unique images and PDFs from sources
    all_images = []
    all_pdfs = []
    seen_images = set()
    seen_pdfs = set()
    
    sources = results['metadatas'][0] if results['metadatas'] else []
    
    # Reorder sources to prioritize the selected product if provided
    if product_id:
        sources = sorted(sources, key=lambda x: x.get('product_id') == product_id, reverse=True)

    for meta in sources:
        # Handle images
        if 'images' in meta:
            import json
            try:
                imgs = json.loads(meta['images']) if isinstance(meta['images'], str) else meta['images']
                for img in imgs:
                    if img['url'] not in seen_images:
                        # Basic relevance check for images
                        if any(kw in img.get('alt', '').lower() or kw in img['url'].lower() for kw in ['product', 'hero', 'main', 'gallery', 'large']):
                            all_images.append(img)
                            seen_images.add(img['url'])
            except: pass
        elif 'image_url' in meta and meta['image_url']:
            if meta['image_url'] not in seen_images:
                all_images.append({"url": meta['image_url'], "alt": "Product Image"})
                seen_images.add(meta['image_url'])
                
        # Handle PDFs
        if 'pdfs' in meta:
            import json
            try:
                pdfs = json.loads(meta['pdfs']) if isinstance(meta['pdfs'], str) else meta['pdfs']
                for pdf in pdfs:
                    if pdf['url'] not in seen_pdfs:
                        # Filter for English manuals
                        title = pdf.get('title', '').upper()
                        url_upper = pdf['url'].upper()
                        
                        is_english = any(kw in title or kw in url_upper for kw in ["ENGLISH", " EN ", "_EN", "MANUAL", "USER GUIDE", "DATASHEET"])
                        is_other_lang = any(kw in title for kw in ["FRENCH", "GERMAN", "ITALIAN", "SPANISH", "CHINESE", "FRANCAIS", "DEUTSCH", "ITALIANO", "ESPANOL"])
                        
                        if is_english or not is_other_lang:
                            all_pdfs.append(pdf)
                            seen_pdfs.add(pdf['url'])
            except: pass

    # Extract Brand Logos
    brand_logos = []
    seen_brands = set()
    
    # If brand_id is provided in request, prioritize it
    if brand_id:
        seen_brands.add(brand_id)
    
    # Also look for brand_ids in the sources
    for meta in sources:
        if 'brand_id' in meta:
            try:
                b_id = int(meta['brand_id'])
                seen_brands.add(b_id)
            except: pass
            
    if seen_brands:
        try:
            session = next(get_session())
            # Convert set to list for SQLModel
            statement = select(Brand).where(Brand.id.in_(list(seen_brands)))
            brands = session.exec(statement).all()
            for b in brands:
                if b.logo_url:
                    brand_logos.append({"name": b.name, "url": b.logo_url})
        except Exception as e:
            print(f"Error fetching brand logos: {e}")

    return {
        "answer": answer,
        "sources": sources,
        "images": all_images[:6], # Limit to 6 images
        "pdfs": all_pdfs[:4],      # Limit to 4 PDFs
        "brand_logos": brand_logos
    }

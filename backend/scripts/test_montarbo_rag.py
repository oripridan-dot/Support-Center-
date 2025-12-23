import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.rag_service import ask_question
from app.core.database import get_session
from app.models.sql_models import Brand
from sqlmodel import select

async def test():
    # Get Montarbo Brand ID
    with next(get_session()) as db:
        brand = db.exec(select(Brand).where(Brand.name == "Montarbo")).first()
        brand_id = brand.id if brand else None
        print(f"Montarbo Brand ID: {brand_id}")

    question = "What are the specifications of the Montarbo B115?"
    print(f"Question: {question}")
    
    try:
        response = await ask_question(question, brand_id=brand_id)
        print("\nResponse:\n", response)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())

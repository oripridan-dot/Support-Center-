import asyncio
import os
import sys

# Add the backend directory to sys.path
sys.path.append('/workspaces/Support-Center-/backend')

from app.services.rag_service import ask_question

async def test():
    try:
        response = await ask_question("Tell me about the Dlive Accessories", brand_id=28)
        print("Response:", response)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test())

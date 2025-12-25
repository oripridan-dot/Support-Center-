from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
import uuid

class VectorDBService:
    def __init__(self):
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = "halilit_products"
        # We defer collection creation to avoid errors if Qdrant isn't running during import
        # But for simplicity in this plan, we'll assume it's running or handle errors gracefully in methods

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE), # nomic-embed-text is 768d
                )
        except Exception as e:
            print(f"Warning: Could not connect to Qdrant: {e}")

    def upsert_document(self, text: str, embedding: list, metadata: dict):
        self._ensure_collection()
        point_id = str(uuid.uuid4())
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={"text": text, **metadata}
                )
            ]
        )

    def search(self, query_vector: list, limit: int = 5, filter_criteria: dict = None):
        self._ensure_collection()
        query_filter = None
        if filter_criteria:
            must_conditions = []
            for key, value in filter_criteria.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                )
            query_filter = models.Filter(must=must_conditions)

        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter
        )

vector_db = VectorDBService()

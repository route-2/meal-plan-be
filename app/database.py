import os
import redis
from dotenv import load_dotenv
from pinecone import Pinecone

# Load environment variables
load_dotenv()

# Initialize Redis client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True  # Ensures output is returned as strings
)

# Initialize Pinecone client
pinecone_api_key = os.getenv("PINECONE_API_KEY")

if not pinecone_api_key:
    raise ValueError("PINECONE_API_KEY is missing. Check your .env file.")

pc = Pinecone(api_key=pinecone_api_key)

# Connect to Pinecone index
index_name = os.getenv("PINECONE_INDEX")

if index_name not in pc.list_indexes().names():
    pc.create_index(name=index_name, dimension=3072, metric="cosine")

index = pc.Index(index_name)

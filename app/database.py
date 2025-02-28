import os
from dotenv import load_dotenv
from pinecone import Pinecone

# Load environment variables from .env
load_dotenv()

# Ensure API key is properly set
pinecone_api_key = os.getenv("PINECONE_API_KEY")

if not pinecone_api_key:
    raise ValueError("PINECONE_API_KEY is missing. Check your .env file.")

# Initialize Pinecone client
pc = Pinecone(api_key=pinecone_api_key)

# Connect to the existing Pinecone index
index_name = os.getenv("PINECONE_INDEX")

if index_name not in pc.list_indexes().names():
    pc.create_index(name=index_name, dimension=3072, metric="cosine")

index = pc.Index(index_name)
print(pc.list_indexes().names())
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from pinecone import Pinecone

def get_pinecone_index():
    api_key = os.getenv("PINECONE_API_KEY")
    host = os.getenv("PINECONE_HOST")
    index_name = os.getenv("PINECONE_INDEX")

    if not api_key or not (host or index_name):
        return None

    pc = Pinecone(api_key=api_key)
    if host:
        return pc.Index(host=host)
    return pc.Index(index_name)

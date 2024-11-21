import os
import openai
import pinecone
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.utils import Parser
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken

router = APIRouter()

tokenizer = tiktoken.get_encoding('cl100k_base')

def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

pc = Pinecone(
    api_key=os.environ.get("PINECONE_API_KEY"),  # Replace with your Pinecone API key
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=20,
    length_function=tiktoken_len,
    separators=["\n\n", "\n", " ", ""]
)

openai.api_key = "YOUR_OPENAI_API_KEY"  # Make sure to set this properly

# OpenAI embedding generation function using LangChain
def get_embedding(text: str):
    """Generate embeddings using OpenAI's model"""
    embedding_model = OpenAIEmbeddings(openai_api_key=openai.api_key)
    embedding = embedding_model.embed_documents(text)
    
    # Convert embedding to float32 before returning
    return np.array(embedding, dtype=np.float32)

@router.post("/upload-document/")
async def upload_document(
    index_name: str = Form(),
    namespace: str = Form(None),
    title: str = Form(),
    author: str = Form(),
    source: str = Form(),
    file: UploadFile = File(...)
):
    try:
        # Parse and process the document (use your parser to extract text)
        parser = Parser(file, title, author, source)  # Pass the required arguments to the Parser
        parsed_data = parser.pdf_data  # Get the parsed document data

        # Generate embedding for the extracted text
        embedding = get_embedding(parsed_data['text'])

        # Prepare metadata to store in Pinecone
        metadata = parsed_data['metadata']

        # Initialize Pinecone index
        index = pinecone.Index(index_name)

        # Prepare the data to upsert (upload the embedding to Pinecone)
        upsert_data = [{
            "id": parsed_data['id'],
            "values": embedding.tolist(),  # Convert embedding to a list for Pinecone
            "metadata": metadata
        }]

        # Upsert the data to Pinecone
        index.upsert(vectors=upsert_data, namespace=namespace)

        return {"message": "Successfully parsed the PDF file and added it to the knowledge base"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
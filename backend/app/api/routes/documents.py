import os
import openai
from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from app.utils import Parser
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import shutil
import time
from uuid import uuid4
from tqdm.auto import tqdm

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
    chunk_size=500,
    chunk_overlap=100,
    length_function=tiktoken_len,
    separators=["\n\n", "\n", " ", ""]
)

spec = ServerlessSpec(
    cloud="aws", region="us-east-1"
)

openai.api_key = "YOUR_OPENAI_API_KEY"  # Make sure to set this properly

embed = OpenAIEmbeddings(model="text-embedding-3-small")

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
        # Normalize index name
        index_name = index_name.replace(" ", "-").lower()
        
        # Save uploaded file temporarily
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        # Parse the uploaded file
        parser = Parser(file_path, title, author, source)

        # Split text into chunks
        chunks = text_splitter.split_text(parser.pdf_data['text'])

        # Define Pinecone index name and check existence
        index_name = 'langchain-retrieval-augmentation'
        existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

        if index_name not in existing_indexes:
            # Create index if it doesn't exist
            pc.create_index(
                index_name,
                dimension=1536,
                metric='dotproduct',
                spec=spec
            )
        # Wait for index initialization
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)

        # Connect to index
        index = pc.Index(index_name)
        time.sleep(1)

        # Metadata fields
        texts = []
        metadatas = []
        batch_limit = 100

        # Prepare and insert chunks with metadata into Pinecone
        for i, text_chunk in enumerate(tqdm(chunks)):
            # Metadata for each chunk
            metadata = {
                'title': title,
                'source': source,
                'category': namespace or 'Default'  # Use namespace as category or 'Default'
            }
            # Append the text and metadata
            texts.append(text_chunk)
            metadatas.append({
                "chunk": i,
                "text": text_chunk,
                **metadata
            })

            # Process in batches
            if len(texts) >= batch_limit:
                ids = [str(uuid4()) for _ in range(len(texts))]
                embeds = embed.embed_documents(texts)  # Generate embeddings
                index.upsert(vectors=zip(ids, embeds, metadatas))  # Upload to Pinecone
                texts, metadatas = [], []  # Clear batch

        # Insert remaining data
        if texts:
            ids = [str(uuid4()) for _ in range(len(texts))]
            embeds = embed.embed_documents(texts)
            index.upsert(vectors=zip(ids, embeds, metadatas), namespace=namespace)
        
        # Remove the temporary file
        os.remove(file_path)

        return {"message": "Successfully parsed the PDF file and added it to the knowledge base"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
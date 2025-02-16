import os
from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from app.utils import Parser
from app.models.documents import DeleteDocumentRequest
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import shutil
import time
from uuid import uuid4
from tqdm.auto import tqdm
from fastapi import HTTPException

router = APIRouter()

tokenizer = tiktoken.get_encoding('cl100k_base')

def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

pc = Pinecone()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    length_function=tiktoken_len,
    separators=["\n\n", "\n", " ", ""]
)

spec = ServerlessSpec(
    cloud="aws", region="us-east-1"
)

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
        # Prepare and insert chunks with metadata into Pinecone
        batch_limit = 100
        texts, metadatas = [], []
        chunk_counter = 0  # Global counter for chunks
        document_id = str(uuid4())[:8]  # Create a unique document identifier

        for i, text_chunk in enumerate(chunks):
            metadata = {
                'title': title,
                'source': source,
                'category': namespace or 'Default',
                'document_id': document_id  # Add document_id to metadata
            }
            texts.append(text_chunk)
            metadatas.append({
                "chunk": chunk_counter,  # Use the global counter
                "text": text_chunk,
                **metadata
            })

            if len(texts) >= batch_limit:
                # Generate unique IDs using document_id and chunk_counter
                ids = [f"{document_id}_chunk_{i+chunk_counter}" for i in range(len(texts))]
                print("Batch IDs:", ids)
                embeds = embed.embed_documents(texts)
                index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)
                chunk_counter += len(texts)  # Increment the counter by batch size
                texts, metadatas = [], []

        # Insert remaining data
        if texts:
            ids = [f"{document_id}_chunk_{i+chunk_counter}" for i in range(len(texts))]
            print("Final batch IDs:", ids)
            embeds = embed.embed_documents(texts)
            index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)

        
        # Remove the temporary file
        os.remove(file_path)

        return {"message": "Successfully parsed the PDF file and added it to the knowledge base"}
    except Exception as e:
        print("An error occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-document")
async def delete_document(request: DeleteDocumentRequest):
    """
    Deletes all records in the Pinecone index that match the given title.
    """
    try:
        # Validate input: Title must be provided
        if not request.title:
            raise HTTPException(
                status_code=400,
                detail="You must provide a 'title' for deletion."
            )

        # Generate title-based prefix for deletion
        title_prefix = f"{request.title.replace(' ', '_').lower()}_chunk_"

        # Connect to the Pinecone index
        index = pc.Index("test-latest-index")
        namespace = "test-latest-namespace"

        # Fetch all IDs matching the prefix
        all_ids = []
        for ids in index.list(prefix=title_prefix, namespace=namespace):
            all_ids.extend(ids)
            index.delete(ids=ids, namespace=namespace)

        return {
            "message": f"Successfully deleted all chunks for title '{request.title}'.",
            "deleted_ids": all_ids,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


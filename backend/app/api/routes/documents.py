import os
from fastapi import APIRouter, UploadFile, HTTPException, File, Form, Depends
from app.utils import Parser, TxtParser, JsonlParser
from app.models.schemas.document import DeleteDocumentRequest, UploadDocumentResponse, DeleteDocumentResponse
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import shutil
import time
import json
from uuid import uuid4
from tqdm.auto import tqdm
import re
from app.api.deps import LanguageDep
from app.core.i18n import get_translation

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
    chunk_overlap=50,
    length_function=tiktoken_len,
    separators=["\n\n", "\n", " ", ""]
)

spec = ServerlessSpec(
    cloud="aws", region="us-east-1"
)

embed = OpenAIEmbeddings(model="text-embedding-3-small")  # This outputs 1536 dimensions

def clean_text(text):
    """
    Clean and normalize text to handle special characters properly and 
    improve readability by removing unwanted line breaks.
    """
    if not text:
        return ""
    
    # Replace escaped newlines with spaces
    text = text.replace('\\n', ' ')
    text = text.replace('\\t', ' ')
    text = text.replace('\\r', ' ')
    
    # Smart newline handling - keep paragraph breaks but not mid-sentence breaks
    # Replace newlines that break sentences (not after periods, question marks, exclamation points)
    text = re.sub(r'([^.!?])\n([^\n])', r'\1 \2', text)
    
    # Keep paragraph breaks (double newlines)
    text = re.sub(r'\n{2,}', ' \n\n ', text)
    
    # Optional: completely remove all newlines for a totally continuous text
    # Uncomment the following line if you want NO newlines at all
    # text = text.replace('\n', ' ')
    
    # Replace multiple spaces with a single space
    text = re.sub(r' +', ' ', text)
    
    return text.strip()

@router.post("/upload-document/pdf/", response_model=UploadDocumentResponse)
async def upload_document(
    language: LanguageDep,
    index_name: str = Form(),
    namespace: str = Form(None),
    book_title: str = Form(),
    author: str = Form(),
    source: str = Form(),
    topic: str = Form(),
    file: UploadFile = File(...),
):
    """
    Upload a PDF document to be processed, chunked, and stored in Pinecone.
    """
    file_path = None
    try:
        # Check file extension
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail=get_translation("invalid_file_format", language, format="PDF")
            )
        
        # Normalize index name
        index_name = index_name.replace(" ", "-").lower()
        
        # Save uploaded file temporarily
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        # Parse the uploaded file
        parser = Parser(file_path, book_title, author, source)

        # Apply aggressive cleaning to completely remove all newlines if you prefer
        # This will make text fully continuous with no line breaks
        completely_cleaned_text = parser.pdf_data['text'].replace('\n', ' ')
        completely_cleaned_text = re.sub(r' +', ' ', completely_cleaned_text)
        
        # Use either the standard cleaned text or the completely cleaned version
        # depending on your preference:
        
        # Option 1: Use parser's cleaned text (keeps paragraph breaks)
        # cleaned_text = clean_text(parser.pdf_data['text'])
        
        # Option 2: Use completely cleaned text (no line breaks at all)
        cleaned_text = completely_cleaned_text
        
        # Split text into chunks using cleaned text
        chunks = text_splitter.split_text(cleaned_text)
        total_chunks = len(chunks)

        # Define Pinecone index name and check existence
        existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

        if index_name not in existing_indexes:
            # Create index with the correct dimension matching your embedding model
            pc.create_index(
                index_name,
                dimension=1536,  # Use 1536 for text-embedding-ada-002 or 3072 for text-embedding-3-large  # Updated to match text-embedding-3-large
                metric='dotproduct',
                spec=spec
            )
        # Wait for index initialization
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)

        # Connect to index
        index = pc.Index(index_name)
        time.sleep(1)

        # Prepare and insert chunks with metadata into Pinecone
        batch_limit = 100
        texts, metadatas = [], []
        chunk_counter = 0  # Global counter for chunks
        document_id = str(uuid4())[:8]  # Create a unique document identifier
        
        # Create normalized topic prefix and book title
        topic_prefix = topic.lower().replace(" ", "_")
        book_title_prefix = book_title.lower().replace(" ", "_")

        for i, text_chunk in enumerate(chunks):
            # Clean each chunk to ensure proper character handling
            clean_chunk = clean_text(text_chunk)
            
            metadata = {
                'document_id': document_id,
                'topic': topic,
                'book_title': book_title,
                'authors': author,
                'source': source,
                'text': clean_chunk,
                'file_type': 'pdf'
            }
            texts.append(clean_chunk)
            metadatas.append(metadata)

            if len(texts) >= batch_limit:
                ids = [f"{topic_prefix}_{book_title_prefix}_{document_id}_chunk_{i+chunk_counter}" for i in range(len(texts))]
                embeds = embed.embed_documents(texts)
                index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)
                chunk_counter += len(texts)  # Increment the counter by batch size
                texts, metadatas = [], []

        # Insert remaining data
        if texts:
            ids = [f"{topic_prefix}_{book_title_prefix}_{document_id}_chunk_{i+chunk_counter}" for i in range(len(texts))]
            embeds = embed.embed_documents(texts)
            index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)

        
        # Remove the temporary file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        # Update the return response to use the new model
        return UploadDocumentResponse(
            message=get_translation("document_uploaded_successfully", language),
            document_id=document_id,
            chunk_count=total_chunks
        )
    except Exception as e:
        # Ensure temporary file is removed in case of exception
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-document/txt/", response_model=UploadDocumentResponse)
async def upload_txt_document(
    language: LanguageDep,
    index_name: str = Form(),
    namespace: str = Form(None),
    book_title: str = Form(),
    author: str = Form(),
    source: str = Form(),
    topic: str = Form(),
    file: UploadFile = File(...),
):
    """
    Upload a TXT document to be processed, chunked, and stored in Pinecone.
    """
    file_path = None
    try:
        # Check file extension
        if not file.filename.endswith('.txt'):
            raise HTTPException(
                status_code=400, 
                detail=get_translation("invalid_file_format", language, format="TXT")
            )

        # Normalize index name
        index_name = index_name.replace(" ", "-").lower()
        
        # Save uploaded file temporarily
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        # Parse the uploaded TXT file
        parser = TxtParser(file_path, book_title, author, source)

        # Clean the text
        cleaned_text = clean_text(parser.txt_data['text'])
        
        # Split text into chunks
        chunks = text_splitter.split_text(cleaned_text)
        total_chunks = len(chunks)

        # Define Pinecone index name and check existence
        existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

        if index_name not in existing_indexes:
            # Create index with the correct dimension matching your embedding model
            pc.create_index(
                index_name,
                dimension=1536,  # Dimension for text-embedding-3-small
                metric='dotproduct',
                spec=spec
            )
            
        # Wait for index initialization
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)

        # Connect to index
        index = pc.Index(index_name)
        time.sleep(1)

        # Prepare and insert chunks with metadata into Pinecone
        batch_limit = 100
        texts, metadatas = [], []
        chunk_counter = 0  # Global counter for chunks
        document_id = str(uuid4())[:8]  # Create a unique document identifier
        
        # Create normalized topic prefix and book title
        topic_prefix = topic.lower().replace(" ", "_")
        book_title_prefix = book_title.lower().replace(" ", "_")

        for i, text_chunk in enumerate(chunks):
            # Clean each chunk to ensure proper character handling
            clean_chunk = clean_text(text_chunk)
            
            metadata = {
                'document_id': document_id,
                'topic': topic,
                'book_title': book_title,
                'authors': author,
                'source': source,
                'text': clean_chunk,
                'file_type': 'txt'
            }
            texts.append(clean_chunk)
            metadatas.append(metadata)

            if len(texts) >= batch_limit:
                ids = [f"{topic_prefix}_{book_title_prefix}_{document_id}_chunk_{i+chunk_counter}" for i in range(len(texts))]
                embeds = embed.embed_documents(texts)
                index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)
                chunk_counter += len(texts)  # Increment the counter by batch size
                texts, metadatas = [], []

        # Insert remaining data
        if texts:
            ids = [f"{topic_prefix}_{book_title_prefix}_{document_id}_chunk_{i+chunk_counter}" for i in range(len(texts))]
            embeds = embed.embed_documents(texts)
            index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)

        # Remove the temporary file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        return UploadDocumentResponse(
            message=get_translation("document_uploaded_successfully", language),
            document_id=document_id,
            chunk_count=total_chunks
        )
    except Exception as e:
        # Ensure temporary file is removed in case of exception
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-document/jsonl/", response_model=UploadDocumentResponse)
async def upload_jsonl_document(
    language: LanguageDep,
    index_name: str = Form(),
    namespace: str = Form(None),
    book_title: str = Form(),
    author: str = Form(),
    source: str = Form(),
    topic: str = Form(),
    file: UploadFile = File(...),
):
    """
    Upload a JSONL document to be processed, chunked, and stored in Pinecone.
    Each line in the JSONL file should be a valid JSON object.
    """
    file_path = None
    try:
        # Check file extension
        if not file.filename.endswith('.jsonl'):
            raise HTTPException(
                status_code=400, 
                detail=get_translation("invalid_file_format", language, format="JSONL")
            )

        # Normalize index name
        index_name = index_name.replace(" ", "-").lower()
        
        # Save uploaded file temporarily
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        # Parse the uploaded JSONL file
        parser = JsonlParser(file_path, book_title, author, source)
        
        # Define Pinecone index name and check existence
        existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

        if index_name not in existing_indexes:
            # Create index with the correct dimension matching your embedding model
            pc.create_index(
                index_name,
                dimension=1536,  # Dimension for text-embedding-3-small
                metric='dotproduct',
                spec=spec
            )
            
        # Wait for index initialization
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)

        # Connect to index
        index = pc.Index(index_name)
        time.sleep(1)

        # Process each JSONL item
        batch_limit = 100
        texts, metadatas = [], []
        document_id = str(uuid4())[:8]  # Create a unique document identifier
        total_items = len(parser.jsonl_data['items'])
        
        # Create normalized topic prefix and book title
        topic_prefix = topic.lower().replace(" ", "_")
        book_title_prefix = book_title.lower().replace(" ", "_")

        for i, item in enumerate(parser.jsonl_data['items']):
            # For each JSONL item, compose a text representation
            if 'question' in item:
                # Format for question-answer pairs
                text_content = f"Question: {item['question']}\n"
                
                if 'options' in item and isinstance(item['options'], dict):
                    text_content += "Options:\n"
                    for key, value in item['options'].items():
                        text_content += f"{key}: {value}\n"
                
                if 'answer' in item:
                    text_content += f"Answer: {item['answer']}"
                
                # Clean the text
                clean_item_text = clean_text(text_content)
                
                # Create metadata with the original JSON item for reference
                metadata = {
                    'document_id': document_id,
                    'topic': topic,
                    'book_title': book_title,
                    'authors': author,
                    'source': source,
                    'text': clean_item_text,
                    'original_json': json.dumps(item),
                    'file_type': 'jsonl',
                    'item_index': i
                }
                
                texts.append(clean_item_text)
                metadatas.append(metadata)
                
                if len(texts) >= batch_limit:
                    ids = [f"{topic_prefix}_{book_title_prefix}_{document_id}_item_{j}" for j in range(i-len(texts)+1, i+1)]
                    embeds = embed.embed_documents(texts)
                    index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)
                    texts, metadatas = [], []

        # Insert remaining data
        if texts:
            ids = [f"{topic_prefix}_{book_title_prefix}_{document_id}_item_{j}" for j in range(total_items-len(texts), total_items)]
            embeds = embed.embed_documents(texts)
            index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)

        # Remove the temporary file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        return UploadDocumentResponse(
            message=get_translation("document_uploaded_successfully", language),
            document_id=document_id,
            chunk_count=total_items
        )
    except Exception as e:
        # Ensure temporary file is removed in case of exception
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-document", response_model=DeleteDocumentResponse)
async def delete_document(
    request: DeleteDocumentRequest,
    language: LanguageDep
):
    """
    Deletes all records in the Pinecone index that match the given document_id.
    """
    try:
        # Validate input: document_id must be provided
        if not request.document_id:
            raise HTTPException(
                status_code=400,
                detail=get_translation("document_id_required", language)
            )

        # Connect to the Pinecone index
        index = pc.Index("assistant-ai")
        namespace = "doctor-ai-test"

        # Modified to handle title prefix
        deleted_ids = []
        for ids in index.list(namespace=namespace):
            # Filter IDs that contain the document_id
            matching_ids = [id for id in ids if request.document_id in id]
            if matching_ids:
                deleted_ids.extend(matching_ids)
                index.delete(ids=matching_ids, namespace=namespace)

        if not deleted_ids:
            raise HTTPException(
                status_code=404,
                detail=get_translation("document_not_found", language)
            )

        return DeleteDocumentResponse(
            message=get_translation("document_deleted_successfully", language),
            deleted_ids=deleted_ids
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
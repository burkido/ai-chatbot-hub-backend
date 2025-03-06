import os
from fastapi import APIRouter, UploadFile, HTTPException, File, Form
from app.utils import Parser
from app.models.documents import DeleteDocumentRequest, UploadDocumentResponse, DeleteDocumentResponse
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import shutil
import time
from uuid import uuid4
from tqdm.auto import tqdm
from fastapi import HTTPException
import re

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

@router.post("/upload-document/", response_model=UploadDocumentResponse)
async def upload_document(
    index_name: str = Form(),
    namespace: str = Form(None),
    book_title: str = Form(),
    author: str = Form(),
    source: str = Form(),
    topic: str = Form(),
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
        
        # Create normalized title prefix
        topic_prefix = topic.lower().replace(" ", "_")

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
            }
            texts.append(clean_chunk)
            metadatas.append(metadata)

            if len(texts) >= batch_limit:
                ids = [f"{topic_prefix}_{document_id}_chunk_{i+chunk_counter}" for i in range(len(texts))]
                embeds = embed.embed_documents(texts)
                index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)
                chunk_counter += len(texts)  # Increment the counter by batch size
                texts, metadatas = [], []

        # Insert remaining data
        if texts:
            ids = [f"{topic_prefix}_{document_id}_chunk_{i+chunk_counter}" for i in range(len(texts))]
            embeds = embed.embed_documents(texts)
            index.upsert(vectors=list(zip(ids, embeds, metadatas)), namespace=namespace)

        
        # Remove the temporary file
        os.remove(file_path)

        # Update the return response to use the new model
        return UploadDocumentResponse(
            message="Successfully parsed the PDF file and added it to the knowledge base",
            document_id=document_id,
            chunk_count=total_chunks
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-document", response_model=DeleteDocumentResponse)
async def delete_document(request: DeleteDocumentRequest):
    """
    Deletes all records in the Pinecone index that match the given document_id.
    """
    try:
        # Validate input: document_id must be provided
        if not request.document_id:
            raise HTTPException(
                status_code=400,
                detail="You must provide a 'document_id' for deletion."
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
                detail=f"No documents found with document_id '{request.document_id}'"
            )

        return DeleteDocumentResponse(
            message=f"Successfully deleted all chunks for document_id '{request.document_id}'",
            deleted_ids=deleted_ids
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
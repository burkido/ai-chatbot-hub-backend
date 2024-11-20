from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends

from pydantic import BaseModel

from app.api.deps import ChatEngineDep

from app import crud
from app.api.deps import SessionDep, CurrentUser
from app.models.user import User
from app.models.chat import ChatMessage, ChatRequest

import pandas as pd

from typing import List
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage


import fitz
import os
import json

router = APIRouter()

class JSONProcessor:
    def __init__(self, data):
        self.data = data

    def to_json(self, output_file):
        entry = self.data
        transformed_entry = {
            "id": entry["id"],
            "text": entry["text"],
            "source": entry["source"],
            "metadata": {
                "title": entry["metadata"]["title"],
                "author": entry["metadata"]["author"]
            }
        }

        output_data = [transformed_entry]
        
        # Write the transformed data to a JSON file
        with open(output_file, 'w') as file:
            json.dump(output_data, file, indent=2)

class Parser:
    def __init__(self, file_path, title, author, source):
        self.file_path = file_path
        self.title = title
        self.author = author
        self.source = source
        self.pdf_data = self.read_pdf()

    def read_pdf(self):
        pdf_content = ''
        with fitz.open(self.file_path) as file:
            for page in file:
                pdf_content += page.get_text().strip()

        metadata = {
            'title': self.title,
            'author': self.author
        }

        return {
            'id': os.path.basename(self.file_path).split('.')[0],
            'text': pdf_content,
            'source': self.source,
            'metadata': metadata
        }

# Dependency for ChatOpenAI instance
def get_chat_openai() -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7,
        model="gpt-3.5-turbo"
    )

def chat(new_message: str, chat_model: ChatOpenAI, history: List[ChatMessage]) -> str:
    langchain_messages = []
    for msg in history:
        if msg.role == "system":
            langchain_messages.append(SystemMessage(content=msg.content))
        elif msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
        else:
            raise ValueError(f"Unknown role: {msg.role}")
    
    # Add the new user message
    langchain_messages.append(HumanMessage(content=new_message))

    # Get the assistant's response
    response = chat_model(langchain_messages)
    
    return response.content

@router.post("/", response_model=str)
def chat_endpoint(
    chat_request: ChatRequest,
    session: SessionDep,
    current_user: CurrentUser,
    chat_model: ChatOpenAI = Depends(get_chat_openai)
) -> str:
    """
    Chat with the assistant and decrease the user's credit.
    """
    # Get the current user from the database
    user = session.get(User, current_user.id)

    # Check if the user has enough credits
    if user.credit < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    # Decrease the user's credit
    crud.decrease_user_credit(session=session, user=user, amount=1)
    
    # Get the chat response
    response = chat(chat_request.message, chat_model, chat_request.history)
    
    return response

class DocumentRequest(BaseModel):
    title: str
    author: str
    source: str

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
        index_name = index_name.replace(" ", "-").lower()

        print("Index name: ", index_name, "Namespace: ", namespace, "Title: ", title, "Author: ", author, "Source: ", source)
        
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        parser = Parser(file_path, title, author, source)


        jsonl_file_path = f"output_{file.filename.split('.')[0]}.json"
        json_processor = JSONProcessor(parser.pdf_data)
        
        os.remove(file_path)
        json_processor.to_json(jsonl_file_path)
        print("JSON file generated!")
        print("Path of the JSON file is", jsonl_file_path)
        
        Tokenizer.initialize()
        tokenizer = Tokenizer()
        print("Tokenizer initialized!")
        
        kb = KnowledgeBase(index_name)
        print("Knowledge base initialized!")

        if not any(name.endswith(index_name) for name in list_canopy_indexes()):
            print("Creating a new canopy index")
            kb.create_canopy_index()
        else:
            print("Index ${index_name} already exists")

        kb.connect()
        print("Connected to the knowledge base!")

        print("Reading the JSON file")
        data = pd.read_json(jsonl_file_path)
        print("JSON file read successfully!", data.head())

        print("Iterating over the documents")
        documents = [Document(**row) for _, row in data.iterrows()]
        print("Documents iterated successfully!")

        batch_size = 10

        for i in tqdm(range(0, len(documents), batch_size)):
            print(f"Upserting documents {i} to {i+batch_size}")
            kb.upsert(documents=documents[i: i+batch_size], namespace=namespace)
        

        return {"message": "Successfully parsed the PDF file and added it to the knowledge base"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
from canopy.tokenizer import Tokenizer
from canopy.knowledge_base import KnowledgeBase
from canopy.knowledge_base import list_canopy_indexes
from canopy.models.data_models import Document
from tqdm.auto import tqdm
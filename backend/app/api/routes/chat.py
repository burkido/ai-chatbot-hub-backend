from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from app.api.deps import ChatEngineDep

from pydantic import BaseModel

from canopy.models.data_models import Messages, UserMessage, AssistantMessage, SystemMessage

from app.api.deps import SessionDep, CurrentUser
from app.models import User
from app import crud

import pandas as pd

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

def chat(new_message: str, chat_engine: ChatEngineDep) -> str:
    messages = [
        SystemMessage(content="You are a friendly and compassionate virtual doctor. Your goal is to assist people with their health questions. Always respond with kindness and empathy. If you're unsure about an answer, simply say, 'I'm not sure, but I'll do my best to help you.' If someone tries to chat with you as if you're a regular person, kindly remind them, 'I'm a bot, but I'm here to assist you with any health-related concerns.' Your purpose is to provide helpful and supportive guidance."),
        UserMessage(content=new_message)
    ]
    chat_response = chat_engine.chat(messages=messages)
    assistant_response = chat_response.choices[0].message.content
    response = assistant_response, messages + [AssistantMessage(content=assistant_response)]
    return response[0]

@router.post("/chat", response_model=str)
def chat_endpoint(
    chatEngine: ChatEngineDep, 
    message: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> str:
    """
    Chat with the assistant and decrease the user's credit.
    """
    # Get the current user from the database
    user = session.get(User, current_user.id)

    # Check if the user has enough credits
    if user.credit < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    crud.decrease_user_credit(session=session, user=user, amount=1)
    response = chat(message, chatEngine)
    
    return response

class DocumentRequest(BaseModel):
    title: str
    author: str
    source: str

@router.post("/upload-document/")
async def parse_pdf(
    index_name: str = Form(default="a"),
    namespace: str = Form(None),
    title: str = Form(default="a"),
    author: str = Form(default="a"),
    source: str = Form(default="a"),
    file: UploadFile = File(...)
):
    try:
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
            kb.upsert(documents[i: i+batch_size])

        return {"message": "Successfully parsed the PDF file and added it to the knowledge base"}


    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
from canopy.tokenizer import Tokenizer
from canopy.knowledge_base import KnowledgeBase
from canopy.knowledge_base import list_canopy_indexes
from canopy.models.data_models import Document
from tqdm.auto import tqdm
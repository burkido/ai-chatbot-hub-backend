from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import pandas as pd
import os
from canopy.tokenizer import Tokenizer
from canopy.knowledge_base import KnowledgeBase
from canopy.knowledge_base import list_canopy_indexes
from canopy.models.data_models import Document
from tqdm.auto import tqdm
from app.utils import Parser, JSONProcessor

router = APIRouter()

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
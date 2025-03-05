import re
from typing import Dict, Any
import PyPDF2
import docx
import csv
from io import StringIO
import fitz  # PyMuPDF
import html

class Parser:
    """
    Parses different file formats and extracts their content
    """
    
    def __init__(self, file_path: str, title: str = "", author: str = "", source: str = ""):
        self.file_path = file_path
        self.title = title
        self.author = author
        self.source = source
        self.pdf_data = {'text': '', 'metadata': {}}
        self.parse_file()
    
    def parse_file(self):
        """Parse the file based on its extension"""
        if self.file_path.endswith('.pdf'):
            self.parse_pdf()
        elif self.file_path.endswith('.docx'):
            self.parse_docx()
        elif self.file_path.endswith('.txt'):
            self.parse_txt()
        elif self.file_path.endswith('.csv'):
            self.parse_csv()
        else:
            raise ValueError("Unsupported file format")
        
        # Clean the extracted text
        self.pdf_data['text'] = self.clean_text(self.pdf_data['text'])
            
    def parse_pdf(self):
        """Extract text and metadata from PDF"""
        try:
            doc = fitz.open(self.file_path)
            text = ""
            
            for page in doc:
                # Extract text with proper encoding
                page_text = page.get_text("text")
                
                # Normalize text - convert various Unicode forms to standard form
                page_text = self._normalize_text(page_text)
                
                text += page_text + "\n\n"
                
            doc.close()
            
            # Store the extracted data
            self.pdf_data = {
                'text': text.strip(),
                'metadata': {
                    'title': self.title,
                    'author': self.author, 
                    'source': self.source,
                    'pages': len(doc)
                }
            }
        except Exception as e:
            raise Exception(f"Error parsing PDF: {str(e)}")
    
    def parse_docx(self):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(self.file_path)
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
                
            self.pdf_data = {
                'text': text.strip(),
                'metadata': {
                    'title': self.title,
                    'author': self.author,
                    'source': self.source
                }
            }
        except Exception as e:
            raise Exception(f"Error parsing DOCX: {str(e)}")
    
    def parse_txt(self):
        """Extract text from TXT file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                
            self.pdf_data = {
                'text': text.strip(),
                'metadata': {
                    'title': self.title,
                    'author': self.author,
                    'source': self.source
                }
            }
        except Exception as e:
            raise Exception(f"Error parsing TXT: {str(e)}")
    
    def parse_csv(self):
        """Extract text from CSV file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                text_buffer = StringIO()
                for row in csv_reader:
                    text_buffer.write(", ".join(row) + "\n")
                
            self.pdf_data = {
                'text': text_buffer.getvalue().strip(),
                'metadata': {
                    'title': self.title,
                    'author': self.author,
                    'source': self.source
                }
            }
        except Exception as e:
            raise Exception(f"Error parsing CSV: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """
        Clean the text by handling escape characters and normalizing spacing.
        Improves readability by handling unwanted line breaks within sentences.
        """
        if not text:
            return ""
            
        # Replace literal '\n' character sequences with spaces
        text = text.replace("\\n", " ")
        
        # Identify sentence endings (period followed by space or newline)
        # Replace other newlines that likely break sentences with spaces
        text = re.sub(r'(?<!\.\s*)\n(?=[a-zA-Z0-9])', ' ', text)
        
        # Keep paragraph breaks (double newlines)
        text = re.sub(r'\n{2,}', '\n\n', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r' +', ' ', text)
        
        # Remove any control characters except newlines
        text = re.sub(r'[\x00-\x09\x0B-\x1F\x7F]', '', text)
        
        return text.strip()
    
    def _normalize_text(self, text):
        """Normalize text to handle encoding issues."""
        # Unescape HTML entities
        text = html.unescape(text)
        
        # Ensure newlines don't break sentences
        # Keep newlines after periods, question marks, exclamation points
        text = re.sub(r'([^.!?])\n([A-Z][a-z])', r'\1 \2', text)
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x09\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Replace multiple spaces with single spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()

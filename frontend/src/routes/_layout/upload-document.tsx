import { createFileRoute } from '@tanstack/react-router';
import { useRef, useState } from 'react';
import {
  Button,
  Container,
  FormControl,
  FormLabel,
  Input,
  useToast,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Text,
  Box,
  Select,
} from '@chakra-ui/react';
import { useMutation } from '@tanstack/react-query';
import { FileUploadService, FileDeleteService } from "../../client"
import { UploadDocumentResponse, DeleteDocumentResponse } from "../../client/models"

export const Route = createFileRoute('/_layout/upload-document')({
  component: DocumentUploader,
});

// File type enum for better type safety
enum FileType {
  PDF = 'pdf',
  TXT = 'txt',
  JSONL = 'jsonl'
}

// Interface for file type info
interface FileTypeInfo {
  label: string;
  extension: string;
  accept: string;
  description: string;
}

// File type configurations
const fileTypes: Record<FileType, FileTypeInfo> = {
  [FileType.PDF]: {
    label: 'PDF Document',
    extension: '.pdf',
    accept: 'application/pdf',
    description: 'Upload PDF documents like books, papers, or reports.'
  },
  [FileType.TXT]: {
    label: 'Text Document',
    extension: '.txt',
    accept: 'text/plain',
    description: 'Plain text files containing knowledge base content.'
  },
  [FileType.JSONL]: {
    label: 'JSONL Document',
    extension: '.jsonl',
    accept: 'application/jsonl,.jsonl',
    description: 'JSON Lines format for Q&A pairs with questions, options, and answers.'
  }
}

function DocumentUploader() {
  const [namespace, setNamespace] = useState('doctor-ai');
  const [indexName, setIndexName] = useState('assistant-ai');
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [bookTitle, setBookTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [source, setSource] = useState('');
  const [topic, setTopic] = useState('');
  const [fileType, setFileType] = useState<FileType>(FileType.PDF);
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState(false);
  const [documentId, setDocumentId] = useState('');
  const [uploadedDocumentId, setUploadedDocumentId] = useState('');
  const [chunkCount, setChunkCount] = useState(0);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const selectedFile = event.target.files[0];
      const maxSizeInBytes = 100 * 1024 * 1024; // 100 MB

      if (selectedFile.size > maxSizeInBytes) {
        toast({
          title: 'File size exceeds the limit',
          description: 'Please upload a file smaller than 100 MB.',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        setFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        return;
      }

      // Validate file extension based on selected file type
      const fileExtension = selectedFile.name.split('.').pop()?.toLowerCase() || '';
      const expectedExtension = fileTypes[fileType].extension.replace('.', '');
      
      if (fileExtension !== expectedExtension) {
        toast({
          title: 'Invalid file type',
          description: `Please upload a ${fileTypes[fileType].extension} file when "${fileTypes[fileType].label}" is selected.`,
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        setFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        return;
      }

      setFile(selectedFile);
    }
  };

  const handleFileTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newFileType = e.target.value as FileType;
    setFileType(newFileType);
    
    // Clear the file selection when changing file type
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const uploadMutation = useMutation<UploadDocumentResponse, Error, { formData: FormData, type: FileType }>({
    mutationFn: async ({ formData, type }) => {
      switch (type) {
        case FileType.PDF:
          return FileUploadService.uploadPdfDocument({ formData });
        case FileType.TXT:
          return FileUploadService.uploadTxtDocument({ formData });
        case FileType.JSONL:
          return FileUploadService.uploadJsonlDocument({ formData });
        default:
          throw new Error(`Unsupported file type: ${type}`);
      }
    },
    onSuccess: (response) => {
      setUploadSuccess(true);
      setUploadError(false);
      setIsLoading(false);
      setUploadedDocumentId(response.document_id);
      setChunkCount(response.chunk_count);
      
      toast({
        title: 'Upload Successful',
        description: `${fileTypes[fileType].label} was successfully uploaded with ID: ${response.document_id}`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      // Reset only file input, keep other form fields
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    onError: (error) => {
      setUploadSuccess(false);
      setUploadError(true);
      setIsLoading(false);
      
      toast({
        title: 'Upload Failed',
        description: error.message || 'An error occurred during upload',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  const handleUpload = async () => {
    if (!indexName || !bookTitle || !author || !source || !topic) {
      toast({
        title: 'Please fill all required fields',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!file) {
      toast({
        title: 'No file selected',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    confirmUpload();
  };

  const confirmUpload = async () => {
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', file as Blob);
    formData.append('index_name', indexName.toLowerCase().replace(/\s+/g, '-'));
    formData.append('namespace', namespace);
    formData.append('book_title', bookTitle);
    formData.append('author', author);
    formData.append('source', source);
    formData.append('topic', topic);

    uploadMutation.mutate({ formData, type: fileType });
  };

  const deleteMutation = useMutation<DeleteDocumentResponse, Error, { document_id: string }>({
    mutationFn: async (data: { document_id: string }) => {
      return FileDeleteService.deleteDocument(data);
    },
    onSuccess: (response) => {
      toast({
        title: 'Document deleted successfully',
        description: `Deleted ${response.deleted_ids.length} chunks`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      setIsLoading(false);
      setDocumentId('');
    },
    onError: (error: any) => {
      toast({
        title: 'Document deletion failed',
        description: error.message,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      setIsLoading(false);
    },
  });

  const confirmDelete = async () => {
    if (!documentId) {
      toast({
        title: "Error",
        description: "You must provide a document ID for deletion.",
        status: "error",
        duration: 2000,
        isClosable: true,
      });
      return;
    }

    setIsLoading(true);
    deleteMutation.mutate({ document_id: documentId });
  };

  return (
    <Container maxW="full" mt={8}>
      <Tabs isFitted variant="enclosed">
        <TabList mb="1em">
          <Tab>Add Document</Tab>
          <Tab>Delete Document</Tab>
        </TabList>
        <TabPanels>
          <TabPanel>
            {/* File type selection */}
            <FormControl mt={4} isRequired>
              <FormLabel htmlFor="fileType">Document Type</FormLabel>
              <Select
                id="fileType"
                value={fileType}
                onChange={handleFileTypeChange}
              >
                {Object.entries(fileTypes).map(([type, info]) => (
                  <option key={type} value={type}>
                    {info.label}
                  </option>
                ))}
              </Select>
              <Text fontSize="sm" color="gray.600" mt={1}>
                {fileTypes[fileType].description}
              </Text>
            </FormControl>

            <FormControl mt={4} isRequired>
              <FormLabel htmlFor="indexName">Index Name</FormLabel>
              <Input
                id="indexName"
                value={indexName}
                onChange={(e) => setIndexName(e.target.value)}
                placeholder="Index Name"
                type="text"
              />
            </FormControl>
            <FormControl mt={4} isRequired>
              <FormLabel htmlFor="namespace">Namespace</FormLabel>
              <Input
                id="namespace"
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                placeholder="Namespace"
                type="text"
              />
            </FormControl>
            <FormControl mt={4} isRequired>
              <FormLabel htmlFor="bookTitle">Book Title</FormLabel>
              <Input
                id="bookTitle"
                value={bookTitle}
                onChange={(e) => setBookTitle(e.target.value)}
                placeholder="Book Title"
                type="text"
              />
            </FormControl>
            <FormControl mt={4} isRequired>
              <FormLabel htmlFor="author">Author</FormLabel>
              <Input
                id="author"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="Author"
                type="text"
              />
            </FormControl>
            <FormControl mt={4} isRequired>
              <FormLabel htmlFor="source">Source</FormLabel>
              <Input
                id="source"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="Source"
                type="text"
              />
            </FormControl>
            <FormControl mt={4} isRequired>
              <FormLabel htmlFor="topic">Topic</FormLabel>
              <Input
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Topic"
                type="text"
              />
            </FormControl>
            <FormControl mt={4} isRequired>
              <FormLabel htmlFor="file">File</FormLabel>
              <Input
                id="file"
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept={fileTypes[fileType].accept}
              />
              <Text fontSize="sm" color="gray.600" mt={1}>
                Only {fileTypes[fileType].extension} files are accepted. {
                  fileType === FileType.JSONL && 
                  "JSONL should contain records with 'question', 'options', and 'answer' fields."
                }
              </Text>
            </FormControl>
            {uploadSuccess && (
              <Alert status="success" mt={4}>
                <AlertIcon />
                <AlertTitle>Success!</AlertTitle>
                <AlertDescription>
                  File uploaded successfully.
                  {uploadedDocumentId && (
                    <Box mt={2}>
                      <Text fontWeight="bold">Document ID: {uploadedDocumentId}</Text>
                      <Text>Chunks uploaded to Pinecone: {chunkCount}</Text>
                      <Text fontSize="sm">Save this ID if you may need to delete this document later</Text>
                    </Box>
                  )}
                </AlertDescription>
              </Alert>
            )}
            {uploadError && (
              <Alert status="error" mt={4}>
                <AlertIcon />
                <AlertTitle>Error!</AlertTitle>
                <AlertDescription>Failed to upload file.</AlertDescription>
              </Alert>
            )}
            <Button variant="primary" mt={4} onClick={handleUpload} isLoading={isLoading}>
              Upload Document
            </Button>
          </TabPanel>
          <TabPanel>
            <FormControl>
              <FormLabel htmlFor="documentId">Document ID</FormLabel>
              <Input
                id="documentId"
                value={documentId}
                onChange={(e) => setDocumentId(e.target.value)}
                placeholder="Document ID"
                type="text"
              />
            </FormControl>
            <Button 
              colorScheme="red" 
              mt={4} 
              onClick={confirmDelete} 
              isLoading={isLoading}
            >
              Delete
            </Button>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  );
}

export default DocumentUploader;
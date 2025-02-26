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
} from '@chakra-ui/react';
import { useMutation } from '@tanstack/react-query';
import { FileUploadService, FileDeleteService } from "../../client"
import { UploadDocumentResponse, DeleteDocumentResponse } from "../../client/models"

export const Route = createFileRoute('/_layout/upload-document')({
  component: UploadPDF,
});

function UploadPDF() {
  const [namespace, setNamespace] = useState('doctor-ai');
  const [indexName, setIndexName] = useState('assistant-ai');
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [bookTitle, setBookTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [source, setSource] = useState('');
  const [topic, setTopic] = useState('');
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

      setFile(selectedFile);
    }
  };

  const mutation = useMutation<UploadDocumentResponse, Error, FormData>({
    mutationFn: async (formData: FormData) => {
      return FileUploadService.uploadDocument({ formData });
    },
    onSuccess: (response) => {
      setUploadSuccess(true);
      setUploadError(false);
      setIsLoading(false);
      setUploadedDocumentId(response.document_id);
      setChunkCount(response.chunk_count);
    },
    onError: () => {
      setUploadSuccess(false);
      setUploadError(true);
      setIsLoading(false);
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

    mutation.mutate(formData);
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
              />
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
              Save
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

export default UploadPDF;
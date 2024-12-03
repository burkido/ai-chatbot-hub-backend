import { createFileRoute } from '@tanstack/react-router';
import { useRef, useState } from 'react';
import {
  Button,
  Container,
  FormControl,
  FormLabel,
  Input,
  useToast,
  useDisclosure,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import { useMutation } from '@tanstack/react-query';
import { FileUploadService, FileDeleteService } from "../../client"

export const Route = createFileRoute('/_layout/upload-document')({
  component: UploadPDF,
});

function UploadPDF() {
  const [namespace, setNamespace] = useState('');
  const [indexName, setIndexName] = useState('quickstart-index');
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [source, setSource] = useState('');
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState(false);

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
        setFileName('');
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        return;
      }

      setFile(selectedFile);
      setFileName(selectedFile.name);
    }
  };

  const mutation = useMutation({
    mutationFn: async (formData: FormData) => {
      return FileUploadService.uploadDocument({ formData });
    },
    onSuccess: () => {
      setUploadSuccess(true);
      setUploadError(false);
      setIsLoading(false);
    },
    onError: () => {
      setUploadSuccess(false);
      setUploadError(true);
      setIsLoading(false);
    },
  });

  const handleUpload = async () => {
    if (!indexName || !title || !author || !source) {
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
    formData.append('title', title);
    formData.append('author', author);
    formData.append('source', source);

    mutation.mutate(formData);
  };

  const deleteMutation = useMutation({
    mutationFn: async (data: { title?: string; source?: string }) => {
      return FileDeleteService.deleteDocument(data);
    },
    onSuccess: () => {
      toast({
        title: 'File deleted successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      setIsLoading(false);
    },
    onError: (error: any) => {
      toast({
        title: 'File deletion failed',
        description: error.message,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      setIsLoading(false);
    },
  });

  const confirmDelete = async () => {
    if (!title && !source) {
      toast({
        title: "Error",
        description: "You must provide either a 'title' or a 'source' for deletion.",
        status: "error",
        duration: 2000,
        isClosable: true,
      });
      return;
    }

    deleteMutation.mutate({ title, source });
  };

  const handleContainerClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
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
            <FormControl isRequired>
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
              <FormLabel htmlFor="title">Title</FormLabel>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Title"
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
                <AlertDescription>File uploaded successfully.</AlertDescription>
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
              <FormLabel htmlFor="title">Title</FormLabel>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Title"
                type="text"
              />
            </FormControl>
            <FormControl mt={4}>
              <FormLabel htmlFor="source">Source</FormLabel>
              <Input
                id="source"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="Source"
                type="text"
              />
            </FormControl>
            <Button variant="danger" mt={4} onClick={confirmDelete} isLoading={isLoading}>
              Delete
            </Button>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  );
}

export default UploadPDF;
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
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
} from '@chakra-ui/react';
import { useMutation } from '@tanstack/react-query';
import { FileUploadService } from "../../client"
// TODO - Add the FileUploadService import

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
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      toast({
        title: 'File uploaded successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      setFile(null);
      setFileName('');
      setIsLoading(false);
    },
    onError: () => {
      toast({
        title: 'File upload failed',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
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

    // If validation is successful, open the confirmation popup
    onOpen();
  };

  const confirmUpload = async () => {
    setIsLoading(true);
    onClose(); // Close the popup immediately after confirming the upload

    const formData = new FormData();
    formData.append('file', file as Blob);
    formData.append('index_name', indexName.toLowerCase().replace(/\s+/g, '-'));
    formData.append('namespace', namespace);
    formData.append('title', title);
    formData.append('author', author);
    formData.append('source', source);

    // Simulate upload progress
    const simulateUploadProgress = () => {
      let progress = 0;
      const interval = setInterval(() => {
        progress += 10;
        if (progress >= 100) {
          clearInterval(interval);
          mutation.mutate(formData);
        }
      }, 300);
    };

    simulateUploadProgress();
  };

  const confirmDelete = () => {
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

    // Call delete API
    // mutation.mutate({ title, source });
    toast({
      title: "Document deleted.",
      status: "success",
      duration: 2000,
      isClosable: true,
    });
  };

  const handleContainerClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <Container maxW="full" mt={8}>
      <Button onClick={onOpen} variant="primary" mb={4}>
        + Add Document
      </Button>
      <Button onClick={onDeleteOpen} variant="danger" mb={4} ml={4}>
        - Delete Document
      </Button>

      <Modal isOpen={isOpen} onClose={onClose} isCentered>
        <ModalOverlay />
        <ModalContent as="form" onSubmit={(e) => { e.preventDefault(); confirmUpload(); }}>
          <ModalHeader>Add Document</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
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
          </ModalBody>

          <ModalFooter gap={3}>
            <Button variant="primary" type="submit" isLoading={isLoading}>
              Save
            </Button>
            <Button onClick={onClose}>Cancel</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <Modal isOpen={isDeleteOpen} onClose={onDeleteClose} isCentered>
        <ModalOverlay />
        <ModalContent as="form" onSubmit={(e) => { e.preventDefault(); confirmDelete(); }}>
          <ModalHeader>Delete Document</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
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
          </ModalBody>
          <ModalFooter gap={3}>
            <Button variant="danger" type="submit">
              Delete
            </Button>
            <Button onClick={onDeleteClose}>Cancel</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
}

export default UploadPDF;
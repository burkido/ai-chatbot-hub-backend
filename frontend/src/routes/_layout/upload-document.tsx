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
  Flex,
  Icon,
  Box,
  Text,
  Spinner,
  Tooltip,
  CircularProgress,
} from '@chakra-ui/react';
import { AttachmentIcon } from '@chakra-ui/icons';
import { useMutation } from '@tanstack/react-query';
import { FileUploadService } from "../../client"

export const Route = createFileRoute('/_layout/upload-document')({
  component: UploadPDF,
});

function UploadPDF() {
  const [namespace, setNamespace] = useState('');
  const [indexName, setIndexName] = useState('quickstart-index');
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [source, setSource] = useState('');
  const { isOpen, onOpen, onClose } = useDisclosure();
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
      setUploadProgress(0);
      setIsLoading(false);
    },
    onError: () => {
      toast({
        title: 'File upload failed',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      setUploadProgress(0);
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
        setUploadProgress(progress);
        if (progress >= 100) {
          clearInterval(interval);
          mutation.mutate(formData);
        }
      }, 300);
    };

    simulateUploadProgress();
  };

  const handleContainerClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <Container maxW="full" mt={8}>
      <Flex direction="column" alignItems="flex-start">
        <FormControl id="indexName" mb={4} isRequired>
          <FormLabel>Index Name</FormLabel>
          <Tooltip label="Index name will be converted to lowercase and spaces will be replaced by hyphens" hasArrow>
            <Input
              type="text"
              value={indexName}
              onChange={(e) => setIndexName(e.target.value)}
              borderColor={'gray.300'}
            />
          </Tooltip>
        </FormControl>
        <FormControl id="namespace" mb={4}>
          <FormLabel>Namespace</FormLabel>
          <Input
            type="text"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
          />
        </FormControl>
        <FormControl id="title" mb={4} isRequired>
          <FormLabel>Title</FormLabel>
          <Input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </FormControl>
        <FormControl id="author" mb={4} isRequired>
          <FormLabel>Author</FormLabel>
          <Input
            type="text"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
          />
        </FormControl>
        <FormControl id="source" mb={4} isRequired>
          <FormLabel>Source</FormLabel>
          <Input
            type="text"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          />
        </FormControl>
        <FormControl id="file" mb={4} isRequired>
          <FormLabel>Upload PDF</FormLabel>
          <Tooltip label="No file selected" isDisabled={!!file} hasArrow>
            <Flex
              alignItems="center"
              borderWidth="1px"
              borderRadius="md"
              borderColor={'gray.300'}
              p={2}
              _hover={{ borderColor: 'blue.500' }}
              cursor="pointer"
              onClick={handleContainerClick}
            >
              <Icon as={AttachmentIcon} boxSize={5} color="gray.500" mr={2} />
              <Input
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                display="none"
                ref={fileInputRef}
              />
              <Box>
                {!fileName ? (
                  <Text color="gray.600" fontSize="sm">
                    Drag & drop your file here or click to browse
                  </Text>
                ) : (
                  <Text color="gray.600" fontSize="sm" mt={2}>
                    Selected file: {fileName}
                  </Text>
                )}
              </Box>
            </Flex>
          </Tooltip>
        </FormControl>
        <Button colorScheme="blue" onClick={handleUpload} isDisabled={isLoading}>
          {isLoading ? (
            <CircularProgress isIndeterminate color="blue.500" size="24px" />
          ) : (
            'Upload'
          )}
        </Button>
      </Flex>

      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Confirm Upload</ModalHeader>
          <ModalCloseButton />
          <ModalBody>Are you sure you want to upload this file?</ModalBody>
          <ModalFooter>
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={confirmUpload}
              ml={3}
              disabled={isLoading}
            >
              {isLoading ? <Spinner size="sm" /> : 'Confirm'}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
}

export default UploadPDF;
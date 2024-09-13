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
      return FileUploadService.uploadDocument({ requestBody: formData });
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
      onClose();
    },
    onError: () => {
      toast({
        title: 'File upload failed',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const handleUpload = async () => {
    if (!indexName) {
      toast({
        title: 'Please fill the index name',
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

    const formData = new FormData();
    formData.append('file', file as Blob);
    formData.append('indexName', indexName);
    formData.append('namespace', namespace);

    mutation.mutate(formData);
    setIsLoading(false);
    onClose(); // Close the popup after confirming the upload
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
          <Tooltip label="Please fill the index name" isDisabled={!!indexName} hasArrow>
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
        <Button colorScheme="blue" onClick={handleUpload}>
          Upload
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
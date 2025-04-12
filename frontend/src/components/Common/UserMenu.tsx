import {
  Box,
  IconButton,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Input,
  FormControl,
  FormLabel,
  useDisclosure,
  useToast,
} from "@chakra-ui/react"
import { Link } from "@tanstack/react-router"
import { FaUserAstronaut } from "react-icons/fa"
import { FiLogOut, FiUser, FiKey } from "react-icons/fi"
import { useState } from "react"

import useAuth from "../../hooks/useAuth"
import { getApplicationKey, saveApplicationKey } from "../../utils/applicationKey"

const UserMenu = () => {
  const { logout } = useAuth()
  const { isOpen, onOpen, onClose } = useDisclosure()
  const [applicationKey, setApplicationKey] = useState<string>(getApplicationKey() || "")
  const toast = useToast()

  const handleLogout = async () => {
    logout()
  }

  const handleSaveApplicationKey = () => {
    saveApplicationKey(applicationKey)
    onClose()
    toast({
      title: "Application key updated",
      status: "success",
      duration: 3000,
      isClosable: true,
    })
  }

  return (
    <>
      {/* Desktop */}
      <Box
        display={{ base: "none", md: "block" }}
        position="fixed"
        top={4}
        right={4}
      >
        <Menu>
          <MenuButton
            as={IconButton}
            aria-label="Options"
            icon={<FaUserAstronaut color="white" fontSize="18px" />}
            bg="ui.main"
            isRound
            data-testid="user-menu"
          />
          <MenuList>
            <MenuItem icon={<FiUser fontSize="18px" />} as={Link} to="settings">
              My profile
            </MenuItem>
            <MenuItem 
              icon={<FiKey fontSize="18px" />} 
              onClick={onOpen}
            >
              Update application key
            </MenuItem>
            <MenuItem
              icon={<FiLogOut fontSize="18px" />}
              onClick={handleLogout}
              color="ui.danger"
              fontWeight="bold"
            >
              Log out
            </MenuItem>
          </MenuList>
        </Menu>
      </Box>

      {/* Application Key Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Update Application Key</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <FormControl>
              <FormLabel>Application Key</FormLabel>
              <Input 
                value={applicationKey}
                onChange={(e) => setApplicationKey(e.target.value)}
                placeholder="Enter application key"
              />
            </FormControl>
          </ModalBody>

          <ModalFooter>
            <Button colorScheme="blue" mr={3} onClick={handleSaveApplicationKey}>
              Save
            </Button>
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  )
}

export default UserMenu

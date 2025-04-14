import { Box, Container, Text } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"

import useAuth from "../../hooks/useAuth"
import UserStats from "../../components/Dashboard/UserStats"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
})

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <>
      <Container maxW="full">
        <Box pt={12} m={4}>
          <Text fontSize="2xl">
            Hi, {currentUser?.full_name || currentUser?.email} 👋🏼
          </Text>
          <Text mb={6}>Welcome back, nice to see you again!</Text>
          
          {/* User Statistics Component with graphs and timelapse */}
          {currentUser?.is_superuser && <UserStats />}
        </Box>
      </Container>
    </>
  )
}

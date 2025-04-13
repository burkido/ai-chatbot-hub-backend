import { useState, useEffect } from "react"
import { 
  Box, 
  Heading, 
  Text, 
  Flex, 
  Card, 
  CardHeader, 
  CardBody, 
  Stat, 
  StatLabel, 
  StatNumber, 
  StatHelpText,
  Grid, 
  Select, 
  Spinner,
  Button,
  ButtonGroup,
  useColorModeValue
} from "@chakra-ui/react"
import { UsersService } from "../../client/services"
import { UserStatistics, ApplicationUserStats } from "../../client/models"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"

// Define our time periods
const TIME_PERIODS = {
  "7d": 7,
  "30d": 30,
  "90d": 90,
}

interface ChartData {
  name: string
  date: string
  count: number
  [key: string]: string | number // For application-specific data
}

export const UserStats = () => {
  const [loading, setLoading] = useState(true)
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState<keyof typeof TIME_PERIODS>("30d")
  const [timelapseActive, setTimelapseActive] = useState(false)
  const [timelapseIndex, setTimelapseIndex] = useState(0)
  const [chartData, setChartData] = useState<ChartData[]>([])
  
  const cardBg = useColorModeValue("white", "gray.700")
  const borderColor = useColorModeValue("gray.200", "gray.600")
  
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const days = TIME_PERIODS[selectedPeriod]
        // Calculate start date based on selected period
        const endDate = new Date().toISOString()
        const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString()
        
        const data = await UsersService.getUserStatistics({ 
          start_date: startDate,
          end_date: endDate
          // No api_key parameter will default to current user's application
        })
        setStatistics(data)
        
        // Transform the data for the chart
        if (data.by_application.length > 0) {
          transformDataForChart(data)
        }
      } catch (error) {
        console.error("Error fetching user statistics:", error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [selectedPeriod])
  
  // Format dates for display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric"
    }).format(date)
  }
  
  // Transform data for chart display
  const transformDataForChart = (data: UserStatistics) => {
    if (!data.by_application.length) return
    
    // Get the first application's data points as base
    const firstApp = data.by_application[0]
    
    // Create chart data from the data points
    const newChartData = firstApp.data_points.map((point, index) => {
      const item: ChartData = {
        name: formatDate(point.date),
        date: point.date,
        count: point.count,
      }
      
      // Add data for each application
      data.by_application.forEach(app => {
        if (app.data_points[index]) {
          item[app.application_name] = app.data_points[index].count
        }
      })
      
      return item
    })
    
    setChartData(newChartData)
    
    // Reset timelapse index when new data is loaded
    setTimelapseIndex(0)
  }
  
  // Handle timelapse playback
  useEffect(() => {
    if (!timelapseActive || !chartData.length) return
    
    const timer = setInterval(() => {
      setTimelapseIndex(prev => {
        const nextIndex = prev + 1
        if (nextIndex >= chartData.length) {
          setTimelapseActive(false)
          return 0
        }
        return nextIndex
      })
    }, 700) // Speed of timelapse animation
    
    return () => clearInterval(timer)
  }, [timelapseActive, chartData])
  
  // Toggle timelapse
  const handleTimelapseToggle = () => {
    if (timelapseActive) {
      setTimelapseActive(false)
    } else {
      setTimelapseIndex(0)
      setTimelapseActive(true)
    }
  }
  
  // Get colors for chart lines
  const getLineColor = (index: number) => {
    const colors = ["#3182CE", "#38A169", "#E53E3E", "#D69E2E", "#805AD5", "#DD6B20"]
    return colors[index % colors.length]
  }
  
  // Current timelapse data for display
  const currentTimelapseData = chartData[timelapseIndex]
  
  return (
    <Box mb={8}>
      <Card
        bg={cardBg}
        borderColor={borderColor}
        borderWidth="1px"
        borderRadius="lg"
        overflow="hidden"
        boxShadow="md"
        mb={6}
      >
        <CardHeader>
          <Flex justifyContent="space-between" alignItems="center">
            <Heading size="md">User Statistics</Heading>
            <ButtonGroup size="sm" isAttached variant="outline">
              {Object.keys(TIME_PERIODS).map((period) => (
                <Button
                  key={period}
                  isActive={selectedPeriod === period}
                  onClick={() => setSelectedPeriod(period as keyof typeof TIME_PERIODS)}
                >
                  {period}
                </Button>
              ))}
            </ButtonGroup>
          </Flex>
        </CardHeader>
        <CardBody>
          {loading ? (
            <Flex justifyContent="center" alignItems="center" height="200px">
              <Spinner />
            </Flex>
          ) : statistics ? (
            <>
              <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={4} mb={6}>
                <Stat>
                  <StatLabel>Total Users</StatLabel>
                  <StatNumber>{statistics.total_users.toLocaleString()}</StatNumber>
                  <StatHelpText>Across all applications</StatHelpText>
                </Stat>
                
                <Stat textAlign={{ base: "left", md: "center" }}>
                  <StatLabel>Applications</StatLabel>
                  <StatNumber>{statistics.by_application.length}</StatNumber>
                </Stat>
                
                <Flex justifyContent={{ base: "flex-start", md: "flex-end" }}>
                  <Button 
                    colorScheme={timelapseActive ? "red" : "blue"}
                    onClick={handleTimelapseToggle}
                    disabled={chartData.length === 0}
                  >
                    {timelapseActive ? "Stop Timelapse" : "Play Timelapse"}
                  </Button>
                </Flex>
              </Grid>
              
              {timelapseActive && currentTimelapseData && (
                <Box textAlign="center" mb={4}>
                  <Text fontSize="xl" fontWeight="bold">
                    User Growth Timelapse - {currentTimelapseData.name}
                  </Text>
                </Box>
              )}
              
              <Box height="400px">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={timelapseActive ? chartData.slice(0, timelapseIndex + 1) : chartData}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    {statistics.by_application.map((app, index) => (
                      <Line
                        key={app.application_id}
                        type="monotone"
                        dataKey={app.application_name}
                        stroke={getLineColor(index)}
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </Box>
              
              {/* Application-specific stats */}
              <Box mt={8}>
                <Heading size="md" mb={4}>User Count by Application</Heading>
                <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", xl: "repeat(3, 1fr)" }} gap={4}>
                  {statistics.by_application.map((app) => (
                    <Card key={app.application_id} variant="outline" size="sm">
                      <CardBody>
                        <Stat>
                          <StatLabel>{app.application_name}</StatLabel>
                          <StatNumber>{app.current_count.toLocaleString()}</StatNumber>
                          <StatHelpText>
                            {app.data_points.length > 0 && app.data_points[0].count > 0
                              ? `+${app.current_count - app.data_points[0].count} since ${TIME_PERIODS[selectedPeriod]} days ago`
                              : "No previous data"}
                          </StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>
                  ))}
                </Grid>
              </Box>
            </>
          ) : (
            <Text>No user statistics available</Text>
          )}
        </CardBody>
      </Card>
    </Box>
  )
}

export default UserStats
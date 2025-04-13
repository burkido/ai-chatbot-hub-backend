import { useEffect, useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { addDays, format } from 'date-fns';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { useToast as useChakraToast } from "@chakra-ui/react";
import { UsersService, UserStatistics } from '../../../client';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export const Route = createFileRoute('/_layout/statistics/user-statistics')({
  component: UserStatisticsPage,
});

function UserStatisticsPage() {
  const toast = useChakraToast();
  const [statistics, setStatistics] = useState<UserStatistics | null>(null);
  const [applications, setApplications] = useState<{ id: string; name: string }[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('all');
  const [dateRange, setDateRange] = useState({
    from: addDays(new Date(), -30),
    to: new Date(),
  });
  const [isLoading, setIsLoading] = useState(false);

  // Extract applications from statistics data when it's loaded
  useEffect(() => {
    if (statistics?.by_application) {
      const apps = statistics.by_application.map(app => ({
        id: app.application_id,
        name: app.application_name
      }));
      setApplications(apps);
    }
  }, [statistics]);

  // Fetch user statistics
  const fetchUserStatistics = async () => {
    setIsLoading(true);
    try {
      // Format dates to match the expected format in the backend (YYYY-MM-DD)
      const params: Record<string, string> = {
        start_date: format(dateRange.from, 'yyyy-MM-dd'),
        end_date: format(dateRange.to, 'yyyy-MM-dd'),
      };

      // The application key is automatically added via the X-Application-Key header
      // in the clientConfig.ts interceptor
      const response = await UsersService.getUserStatistics(params);
      setStatistics(response);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch user statistics',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch data when filters change
  useEffect(() => {
    fetchUserStatistics();
  }, [selectedAppId, dateRange]);

  // Prepare data for the chart
  const prepareChartData = () => {
    if (!statistics) return null;

    const datasets = statistics.by_application.map((app) => ({
      label: app.application_name,
      data: app.data_points.map((point) => point.count),
      borderColor: getRandomColor(),
      backgroundColor: 'rgba(0, 0, 0, 0.1)',
      tension: 0.3,
    }));

    const labels = statistics.by_application[0]?.data_points.map((point) =>
      format(new Date(point.date), 'MMM dd')
    ) || [];

    return {
      labels,
      datasets,
    };
  };

  // Generate random colors for chart lines
  const getRandomColor = () => {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
      color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
  };

  const chartData = prepareChartData();
  
  // Handle date range changes
  const handleDateChange = (date: any) => {
    setDateRange(date);
  };

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-semibold">User Statistics</h1>
      
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="w-64">
          <Select
            value={selectedAppId}
            onValueChange={setSelectedAppId}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select Application" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Applications</SelectItem>
              {applications.map((app) => (
                <SelectItem key={app.id} value={app.id}>
                  {app.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <DateRangePicker
          date={dateRange}
          onDateChange={handleDateChange}
        />
        
      </div>

      {/* Total Users Card */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Total Users</CardTitle>
            <CardDescription>All registered users</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {isLoading ? 'Loading...' : statistics?.total_users || 0}
            </div>
          </CardContent>
        </Card>
        
        {statistics?.by_application.map((app) => (
          <Card key={app.application_id}>
            <CardHeader>
              <CardTitle>{app.application_name}</CardTitle>
              <CardDescription>Registered users</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {app.current_count}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Chart Card */}
      <Card>
        <CardHeader>
          <CardTitle>User Growth Over Time</CardTitle>
          <CardDescription>
            New user registrations {format(dateRange.from, 'MMM dd, yyyy')} to {format(dateRange.to, 'MMM dd, yyyy')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-80 items-center justify-center">Loading chart data...</div>
          ) : chartData ? (
            <div className="h-80">
              <Line
                data={chartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  scales: {
                    y: {
                      beginAtZero: true,
                      ticks: {
                        precision: 0,
                      },
                    },
                  },
                }}
              />
            </div>
          ) : (
            <div className="flex h-80 items-center justify-center">No data available</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
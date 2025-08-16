import React, { useState } from 'react';
import axios from 'axios';
import { saveAs } from 'file-saver';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Separator } from './ui/separator';
import { Alert, AlertDescription } from './ui/alert';
import { Download, FileText, FileSpreadsheet, File, Calendar, Filter } from 'lucide-react';

const ExportManager = ({ baseUrl }) => {
  const [loading, setLoading] = useState({});
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    department: '',
    payPeriodStart: '',
    payPeriodEnd: ''
  });

  const handleExport = async (endpoint, filename, format, params = {}) => {
    const exportKey = `${endpoint}_${format}`;
    setLoading(prev => ({ ...prev, [exportKey]: true }));
    setError(null);

    try {
      const response = await axios.get(`${baseUrl}${endpoint}`, {
        params,
        responseType: 'blob',
        timeout: 300000, // 5 minute timeout for large exports
        onDownloadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            console.log(`Download Progress: ${percentCompleted}%`);
          }
        },
      });

      // Extract filename from response headers if available
      const contentDisposition = response.headers['content-disposition'];
      let downloadFilename = filename;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          downloadFilename = filenameMatch[1].replace(/['"]/g, '');
        }
      }

      // Create blob and trigger download
      const blob = new Blob([response.data], { 
        type: response.headers['content-type'] 
      });
      saveAs(blob, downloadFilename);

    } catch (err) {
      const errorMessage = err.response?.data?.detail || 
                          err.message || 
                          'Export failed. Please try again.';
      setError(errorMessage);
      console.error('Export error:', err);
    } finally {
      setLoading(prev => ({ ...prev, [exportKey]: false }));
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const buildParams = (additionalParams = {}) => {
    const params = { ...additionalParams };
    
    Object.entries(filters).forEach(([key, value]) => {
      if (value) {
        params[key] = value;
      }
    });
    
    return params;
  };

  const isLoading = (key) => loading[key] || false;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Export Workforce Data</h2>
        <p className="text-gray-600">Generate detailed reports of your workforce management data</p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Filter Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
          <CardDescription>
            Set date ranges and filters to customize your exports
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <Input
                id="startDate"
                type="date"
                value={filters.startDate}
                onChange={(e) => handleFilterChange('startDate', e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 mb-1">
                End Date
              </label>
              <Input
                id="endDate"
                type="date"
                value={filters.endDate}
                onChange={(e) => handleFilterChange('endDate', e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="department" className="block text-sm font-medium text-gray-700 mb-1">
                Department
              </label>
              <Select value={filters.department} onValueChange={(value) => handleFilterChange('department', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="All Departments" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Departments</SelectItem>
                  <SelectItem value="Support Work">Support Work</SelectItem>
                  <SelectItem value="Community Access">Community Access</SelectItem>
                  <SelectItem value="Administration">Administration</SelectItem>
                  <SelectItem value="Management">Management</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Shift Roster Exports */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Shift Roster Exports
          </CardTitle>
          <CardDescription>
            Export shift roster data with comprehensive employee scheduling information
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => handleExport(
                '/api/export/shift-roster/csv',
                'shift_roster.csv',
                'csv',
                buildParams({ 
                  start_date: filters.startDate, 
                  end_date: filters.endDate,
                  department: filters.department 
                })
              )}
              disabled={isLoading('shift-roster_csv')}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <FileText className="h-4 w-4 mr-2" />
              {isLoading('shift-roster_csv') ? 'Exporting...' : 'Export CSV'}
            </Button>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Includes employee names, shift dates, times, departments, and calculated hours
          </p>
        </CardContent>
      </Card>

      {/* Pay Summary Exports */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Pay Summary Exports
          </CardTitle>
          <CardDescription>
            Export detailed pay calculations and wage summaries
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="payPeriodStart" className="block text-sm font-medium text-gray-700 mb-1">
                  Pay Period Start
                </label>
                <Input
                  id="payPeriodStart"
                  type="date"
                  value={filters.payPeriodStart}
                  onChange={(e) => handleFilterChange('payPeriodStart', e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="payPeriodEnd" className="block text-sm font-medium text-gray-700 mb-1">
                  Pay Period End
                </label>
                <Input
                  id="payPeriodEnd"
                  type="date"
                  value={filters.payPeriodEnd}
                  onChange={(e) => handleFilterChange('payPeriodEnd', e.target.value)}
                />
              </div>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => handleExport(
                '/api/export/pay-summary/csv',
                'pay_summary.csv',
                'csv',
                buildParams({ 
                  pay_period_start: filters.payPeriodStart, 
                  pay_period_end: filters.payPeriodEnd 
                })
              )}
              disabled={isLoading('pay-summary_csv')}
              className="bg-green-600 hover:bg-green-700"
            >
              <FileText className="h-4 w-4 mr-2" />
              {isLoading('pay-summary_csv') ? 'Exporting...' : 'Export CSV'}
            </Button>
            
            <Button
              onClick={() => handleExport(
                '/api/export/pay-summary/pdf',
                'pay_summary.pdf',
                'pdf',
                buildParams({ 
                  pay_period_start: filters.payPeriodStart, 
                  pay_period_end: filters.payPeriodEnd 
                })
              )}
              disabled={isLoading('pay-summary_pdf')}
              className="bg-red-600 hover:bg-red-700"
            >
              <File className="h-4 w-4 mr-2" />
              {isLoading('pay-summary_pdf') ? 'Exporting...' : 'Export PDF'}
            </Button>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Includes regular hours, penalty rates, overtime calculations, and net pay
          </p>
        </CardContent>
      </Card>

      {/* Comprehensive Workforce Data Export */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" />
            Comprehensive Workforce Data
          </CardTitle>
          <CardDescription>
            Export complete workforce management data with multiple sheets
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => handleExport(
                '/api/export/workforce-data/excel',
                'workforce_data.xlsx',
                'excel'
              )}
              disabled={isLoading('workforce-data_excel')}
              className="bg-cyan-600 hover:bg-cyan-700"
            >
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              {isLoading('workforce-data_excel') ? 'Exporting...' : 'Export Excel'}
            </Button>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Includes shift rosters, pay summaries, and employee data in separate sheets
          </p>
        </CardContent>
      </Card>

      <Separator />
      
      <div className="text-center text-sm text-gray-500">
        <p>All exports include timestamped filenames and comprehensive data formatting</p>
        <p>Large exports may take several minutes to process</p>
      </div>
    </div>
  );
};

export default ExportManager;
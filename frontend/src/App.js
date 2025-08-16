import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Calendar } from './components/ui/calendar';
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Switch } from './components/ui/switch';
import { Separator } from './components/ui/separator';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { Users, Calendar as CalendarIcon, Settings, DollarSign, Clock, Download, Plus, Edit } from 'lucide-react';
import ExportManager from './components/ExportManager';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [staff, setStaff] = useState([]);
  const [shiftTemplates, setShiftTemplates] = useState([]);
  const [rosterEntries, setRosterEntries] = useState([]);
  const [settings, setSettings] = useState({
    pay_mode: 'default',
    rates: {
      weekday_day: 42.00,
      weekday_evening: 44.50,
      weekday_night: 48.50,
      saturday: 57.50,
      sunday: 74.00,
      public_holiday: 88.50,
      sleepover_default: 175.00,
      sleepover_schads: 60.02
    }
  });
  const [selectedShift, setSelectedShift] = useState(null);
  const [showShiftDialog, setShowShiftDialog] = useState(false);
  const [showStaffDialog, setShowStaffDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showBreakWarning, setShowBreakWarning] = useState(false);
  const [breakWarningData, setBreakWarningData] = useState(null);
  const [showAddShiftDialog, setShowAddShiftDialog] = useState(false);
  const [newShift, setNewShift] = useState({
    date: '',
    start_time: '09:00',
    end_time: '17:00',
    is_sleepover: false
  });
  const [newStaffName, setNewStaffName] = useState('');
  const [activeTab, setActiveTab] = useState('roster');

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    if (currentDate) {
      fetchRosterData();
    }
  }, [currentDate]);

  const fetchInitialData = async () => {
    try {
      const [staffRes, templatesRes, settingsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/staff`),
        axios.get(`${API_BASE_URL}/api/shift-templates`),
        axios.get(`${API_BASE_URL}/api/settings`)
      ]);
      
      setStaff(staffRes.data);
      setShiftTemplates(templatesRes.data);
      setSettings(settingsRes.data);
    } catch (error) {
      console.error('Error fetching initial data:', error);
    }
  };

  const fetchRosterData = async () => {
    try {
      const monthString = currentDate.toISOString().slice(0, 7); // YYYY-MM
      
      // Get the first day of the current month to check if we need previous month data
      const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
      const startOfWeek = new Date(firstDay);
      startOfWeek.setDate(startOfWeek.getDate() - (firstDay.getDay() + 6) % 7); // Start from Monday
      
      // If the first Monday of the week is from the previous month, fetch that data too
      const requests = [axios.get(`${API_BASE_URL}/api/roster?month=${monthString}`)];
      
      if (startOfWeek.getMonth() !== firstDay.getMonth()) {
        const prevMonthString = startOfWeek.toISOString().slice(0, 7);
        requests.push(axios.get(`${API_BASE_URL}/api/roster?month=${prevMonthString}`));
      }
      
      // Also check if we need next month data for the last week
      const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
      const endOfWeek = new Date(lastDay);
      endOfWeek.setDate(endOfWeek.getDate() + (7 - lastDay.getDay()) % 7); // End of Sunday
      
      if (endOfWeek.getMonth() !== lastDay.getMonth()) {
        const nextMonthString = endOfWeek.toISOString().slice(0, 7);
        requests.push(axios.get(`${API_BASE_URL}/api/roster?month=${nextMonthString}`));
      }
      
      const responses = await Promise.all(requests);
      const allEntries = responses.flatMap(response => response.data);
      
      setRosterEntries(allEntries);
    } catch (error) {
      console.error('Error fetching roster data:', error);
    }
  };

  const generateMonthlyRoster = async () => {
    try {
      const monthString = currentDate.toISOString().slice(0, 7);
      await axios.post(`${API_BASE_URL}/api/generate-roster/${monthString}`);
      
      // Also generate roster for previous month dates if they appear in the first week
      const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
      const startOfWeek = new Date(firstDay);
      startOfWeek.setDate(startOfWeek.getDate() - (firstDay.getDay() + 6) % 7); // Start from Monday
      
      if (startOfWeek.getMonth() !== firstDay.getMonth()) {
        const prevMonthString = startOfWeek.toISOString().slice(0, 7);
        await axios.post(`${API_BASE_URL}/api/generate-roster/${prevMonthString}`);
      }
      
      // Also generate for next month dates if they appear in the last week
      const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
      const endOfWeek = new Date(lastDay);
      endOfWeek.setDate(endOfWeek.getDate() + (7 - lastDay.getDay()) % 7);
      
      if (endOfWeek.getMonth() !== lastDay.getMonth()) {
        const nextMonthString = endOfWeek.toISOString().slice(0, 7);
        await axios.post(`${API_BASE_URL}/api/generate-roster/${nextMonthString}`);
      }
      
      fetchRosterData();
    } catch (error) {
      console.error('Error generating roster:', error);
    }
  };

  const updateRosterEntry = async (entryId, updates) => {
    try {
      const entry = rosterEntries.find(e => e.id === entryId);
      const updatedEntry = { ...entry, ...updates };
      
      const response = await axios.put(`${API_BASE_URL}/api/roster/${entryId}`, updatedEntry);
      console.log('Updated entry:', response.data);
      fetchRosterData();
    } catch (error) {
      console.error('Error updating roster entry:', error);
    }
  };

  const addStaff = async () => {
    if (!newStaffName.trim()) return;
    
    try {
      const newStaff = {
        name: newStaffName,
        active: true
      };
      await axios.post(`${API_BASE_URL}/api/staff`, newStaff);
      setNewStaffName('');
      setShowStaffDialog(false);
      fetchInitialData();
    } catch (error) {
      console.error('Error adding staff:', error);
    }
  };

  const updateSettings = async (newSettings) => {
    try {
      await axios.put(`${API_BASE_URL}/api/settings`, newSettings);
      setSettings(newSettings);
      setShowSettingsDialog(false);
      // Refresh roster to recalculate pay
      fetchRosterData();
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  const updateShiftTemplate = async (templateId, updates) => {
    try {
      const template = shiftTemplates.find(t => t.id === templateId);
      const updatedTemplate = { ...template, ...updates };
      
      await axios.put(`${API_BASE_URL}/api/shift-templates/${templateId}`, updatedTemplate);
      fetchInitialData();
    } catch (error) {
      console.error('Error updating shift template:', error);
    }
  };

  const updateShiftTime = async (entryId, newStartTime, newEndTime) => {
    try {
      const entry = rosterEntries.find(e => e.id === entryId);
      const updatedEntry = { 
        ...entry, 
        start_time: newStartTime, 
        end_time: newEndTime 
      };
      
      await axios.put(`${API_BASE_URL}/api/roster/${entryId}`, updatedEntry);
      fetchRosterData();
    } catch (error) {
      console.error('Error updating shift time:', error);
    }
  };

  const checkShiftBreakViolation = (staffId, staffName, newShift) => {
    if (!staffId || !staffName) return null;

    // Get all shifts for this staff member in the current month
    const staffShifts = rosterEntries.filter(entry => 
      entry.staff_id === staffId && entry.id !== newShift.id
    );

    // Add the new shift to check against
    const allShifts = [...staffShifts, newShift].sort((a, b) => 
      new Date(a.date + 'T' + a.start_time) - new Date(b.date + 'T' + b.start_time)
    );

    for (let i = 0; i < allShifts.length - 1; i++) {
      const currentShift = allShifts[i];
      const nextShift = allShifts[i + 1];

      // Skip if either shift is the new one we're checking
      if (currentShift.id === newShift.id || nextShift.id === newShift.id) {
        // Calculate time between shifts
        const currentEndTime = new Date(currentShift.date + 'T' + currentShift.end_time);
        const nextStartTime = new Date(nextShift.date + 'T' + nextShift.start_time);
        
        // Handle overnight shifts
        if (currentShift.end_time < currentShift.start_time) {
          currentEndTime.setDate(currentEndTime.getDate() + 1);
        }
        if (nextShift.start_time < '12:00' && nextShift.end_time > nextShift.start_time) {
          // Normal day shift starting early
        }

        const timeDiffHours = (nextStartTime - currentEndTime) / (1000 * 60 * 60);

        // Check for violations (less than 10 hours break)
        if (timeDiffHours < 10 && timeDiffHours >= 0) {
          // Check exceptions: sleepover to regular or regular to sleepover
          const currentIsSleepover = currentShift.is_sleepover;
          const nextIsSleepover = nextShift.is_sleepover;
          
          // Allow if going from sleepover to regular or regular to sleepover
          if (currentIsSleepover || nextIsSleepover) {
            continue;
          }

          // Violation found
          return {
            violation: true,
            staffName,
            currentShift,
            nextShift,
            timeBetween: timeDiffHours.toFixed(1),
            message: `${staffName} has only ${timeDiffHours.toFixed(1)} hours break between shifts. Minimum 10 hours required.`,
            details: `${currentShift.date} ${currentShift.start_time}-${currentShift.end_time} → ${nextShift.date} ${nextShift.start_time}-${nextShift.end_time}`
          };
        }
      }
    }

    return null;
  };

  const handleStaffAssignmentWithBreakCheck = (staffId, staffName, shift) => {
    if (!staffId || staffId === "unassigned") {
      // Just unassign
      const updates = {
        staff_id: null,
        staff_name: null,
        start_time: shift.start_time,
        end_time: shift.end_time
      };
      updateRosterEntry(shift.id, updates);
      setShowShiftDialog(false);
      return;
    }

    // Check for break violations
    const violation = checkShiftBreakViolation(staffId, staffName, shift);
    
    if (violation) {
      // Show warning dialog
      setBreakWarningData({
        staffId,
        staffName,
        shift,
        violation
      });
      setShowBreakWarning(true);
    } else {
      // No violation, proceed with assignment
      const updates = {
        staff_id: staffId,
        staff_name: staffName,
        start_time: shift.start_time,
        end_time: shift.end_time
      };
      updateRosterEntry(shift.id, updates);
      setShowShiftDialog(false);
    }
  };

  const approveShiftAssignment = () => {
    if (breakWarningData) {
      const updates = {
        staff_id: breakWarningData.staffId,
        staff_name: breakWarningData.staffName,
        start_time: breakWarningData.shift.start_time,
        end_time: breakWarningData.shift.end_time
      };
      updateRosterEntry(breakWarningData.shift.id, updates);
    }
    setShowBreakWarning(false);
    setBreakWarningData(null);
    setShowShiftDialog(false);
  };

  const denyShiftAssignment = () => {
    setShowBreakWarning(false);
    setBreakWarningData(null);
    // Keep the shift dialog open for user to select different staff
  };

  const clearMonthlyRoster = async () => {
    try {
      const monthString = currentDate.toISOString().slice(0, 7);
      const monthName = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });
      
      // Use a more reliable confirmation method
      if (window.confirm(`⚠️ CLEAR ENTIRE ROSTER\n\nAre you sure you want to delete ALL shifts for ${monthName}?\n\nThis action cannot be undone!`)) {
        console.log('Clearing roster for month:', monthString);
        const response = await axios.delete(`${API_BASE_URL}/api/roster/month/${monthString}`);
        console.log('Clear roster response:', response.data);
        
        // Show success message
        alert(`✅ Successfully cleared all shifts for ${monthName}\n\n${response.data.message}`);
        fetchRosterData();
      }
    } catch (error) {
      console.error('Error clearing roster:', error);
      alert(`❌ Error clearing roster: ${error.response?.data?.message || error.message}`);
    }
  };

  const addIndividualShift = async () => {
    if (!newShift.date || !newShift.start_time || !newShift.end_time) {
      alert('Please fill in all required fields (date, start time, end time)');
      return;
    }
    
    try {
      const shiftData = {
        id: '', // Will be auto-generated by backend
        date: newShift.date,
        shift_template_id: `custom-${Date.now()}`,
        start_time: newShift.start_time,
        end_time: newShift.end_time,
        is_sleepover: newShift.is_sleepover,
        staff_id: null,
        staff_name: null,
        is_public_holiday: false,
        hours_worked: 0.0,
        base_pay: 0.0,
        sleepover_allowance: 0.0,
        total_pay: 0.0
      };
      
      console.log('Adding shift:', shiftData);
      const response = await axios.post(`${API_BASE_URL}/api/roster/add-shift`, shiftData);
      console.log('Shift added successfully:', response.data);
      
      setNewShift({
        date: '',
        start_time: '09:00',
        end_time: '17:00',
        is_sleepover: false
      });
      setShowAddShiftDialog(false);
      fetchRosterData();
    } catch (error) {
      console.error('Error adding shift:', error);
      alert(`Error adding shift: ${error.response?.data?.detail || error.message}`);
    }
  };

  const deleteShift = async (shiftId) => {
    try {
      if (window.confirm('🗑️ DELETE SHIFT\n\nAre you sure you want to delete this shift?\n\nThis action cannot be undone!')) {
        console.log('Deleting shift:', shiftId);
        const response = await axios.delete(`${API_BASE_URL}/api/roster/${shiftId}`);
        console.log('Delete shift response:', response.data);
        fetchRosterData();
      }
    } catch (error) {
      console.error('Error deleting shift:', error);
      alert(`❌ Error deleting shift: ${error.response?.data?.message || error.message}`);
    }
  };

  const getDayEntries = (date) => {
    const dateString = date.toISOString().split('T')[0];
    return rosterEntries.filter(entry => entry.date === dateString);
  };

  const getShiftTypeBadge = (entry) => {
    // Check for manual or automatic sleepover status
    const isSleepover = entry.manual_sleepover !== null ? entry.manual_sleepover : entry.is_sleepover;
    
    if (isSleepover) {
      return <Badge variant="secondary" className="bg-indigo-100 text-indigo-800">Sleepover</Badge>;
    }
    
    // If manual shift type is set, use it
    if (entry.manual_shift_type) {
      const typeMap = {
        'weekday_day': { label: 'Day', class: 'bg-green-100 text-green-800' },
        'weekday_evening': { label: 'Evening', class: 'bg-orange-100 text-orange-800' },
        'weekday_night': { label: 'Night', class: 'bg-purple-100 text-purple-800' },
        'saturday': { label: 'Saturday', class: 'bg-blue-100 text-blue-800' },
        'sunday': { label: 'Sunday', class: 'bg-purple-100 text-purple-800' },
        'public_holiday': { label: 'Public Holiday', class: 'bg-red-100 text-red-800' },
        'sleepover': { label: 'Sleepover', class: 'bg-indigo-100 text-indigo-800' }
      };
      const type = typeMap[entry.manual_shift_type];
      return <Badge variant="secondary" className={type.class}>{type.label}</Badge>;
    }
    
    // Simple automatic detection based on date
    const date = new Date(entry.date);
    const dayOfWeek = date.getDay(); // 0=Sunday, 1=Monday, ..., 6=Saturday
    
    // Weekend check
    if (dayOfWeek === 6) { // Saturday
      return <Badge variant="secondary" className="bg-blue-100 text-blue-800">Saturday</Badge>;
    } else if (dayOfWeek === 0) { // Sunday
      return <Badge variant="secondary" className="bg-purple-100 text-purple-800">Sunday</Badge>;
    }
    
    // Weekday time-based check
    const startHour = parseInt(entry.start_time.split(':')[0]);
    const endHour = parseInt(entry.end_time.split(':')[0]);
    
    // Simple logic for weekdays
    if (startHour < 6 || (endHour <= startHour && endHour > 0)) { // Night or overnight
      return <Badge variant="secondary" className="bg-purple-100 text-purple-800">Night</Badge>;
    } else if (startHour >= 20) { // Evening start
      return <Badge variant="secondary" className="bg-orange-100 text-orange-800">Evening</Badge>;
    } else { // Day
      return <Badge variant="secondary" className="bg-green-100 text-green-800">Day</Badge>;
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD'
    }).format(amount);
  };

  const getWeeklyTotals = () => {
    const weekStart = new Date(currentDate);
    weekStart.setDate(currentDate.getDate() - currentDate.getDay() + 1); // Monday
    
    const weekEntries = rosterEntries.filter(entry => {
      const entryDate = new Date(entry.date);
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      return entryDate >= weekStart && entryDate <= weekEnd;
    });

    const staffTotals = {};
    let totalHours = 0;
    let totalPay = 0;

    weekEntries.forEach(entry => {
      if (entry.staff_name) {
        if (!staffTotals[entry.staff_name]) {
          staffTotals[entry.staff_name] = { hours: 0, pay: 0 };
        }
        staffTotals[entry.staff_name].hours += entry.hours_worked;
        staffTotals[entry.staff_name].pay += entry.total_pay;
        totalHours += entry.hours_worked;
        totalPay += entry.total_pay;
      }
    });

    return { staffTotals, totalHours, totalPay };
  };

  const renderCalendarDay = (date) => {
    const dayEntries = getDayEntries(date);
    const dayTotal = dayEntries.reduce((sum, entry) => sum + entry.total_pay, 0);
    
    // Check if this date is from a different month (previous or next)
    const isCurrentMonth = date.getMonth() === currentDate.getMonth();
    const isPreviousMonth = date < new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
    const isNextMonth = date > new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
    
    // Style classes for different month dates
    const backgroundClass = isCurrentMonth 
      ? 'bg-white' 
      : isPreviousMonth 
        ? 'bg-slate-100' 
        : 'bg-slate-50';
    
    const textClass = isCurrentMonth 
      ? 'text-slate-900' 
      : 'text-slate-500';
    
    return (
      <div className={`min-h-[120px] p-1 border-r border-b border-slate-200 ${backgroundClass}`}>
        <div className={`font-medium text-sm mb-2 flex items-center justify-between ${textClass}`}>
          <span>{date.getDate()}</span>
          {!isCurrentMonth && (
            <span className="text-xs text-slate-400">
              {isPreviousMonth ? 'Prev' : 'Next'}
            </span>
          )}
        </div>
        <div className="space-y-1">
          {dayEntries.map(entry => (
            <div
              key={entry.id}
              className="text-xs p-1 rounded cursor-pointer hover:bg-slate-200 transition-colors group relative"
            >
              <div 
                className="flex-1"
                onClick={() => {
                  setSelectedShift(entry);
                  setShowShiftDialog(true);
                }}
              >
                <div className="font-medium flex items-center justify-between">
                  <span className={isCurrentMonth ? '' : 'opacity-75'}>
                    {entry.start_time}-{entry.end_time}
                  </span>
                  <Edit className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className={`text-slate-600 ${isCurrentMonth ? '' : 'opacity-75'}`}>
                  {entry.staff_name || 'Unassigned'}
                </div>
                <div className="flex items-center justify-between">
                  <div className={isCurrentMonth ? '' : 'opacity-75'}>
                    {getShiftTypeBadge(entry)}
                  </div>
                  <span className={`font-medium text-emerald-600 ${isCurrentMonth ? '' : 'opacity-75'}`}>
                    {formatCurrency(entry.total_pay)}
                  </span>
                </div>
              </div>
              <button
                className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 flex items-center justify-center hover:bg-red-600 transition-all z-10 shadow-sm border border-white"
                onClick={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  console.log('Delete button clicked for shift:', entry.id);
                  deleteShift(entry.id);
                }}
                title="Delete shift"
                style={{ fontSize: '10px', lineHeight: '1' }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
        {dayTotal > 0 && (
          <div className={`mt-2 pt-1 border-t border-slate-200 text-xs font-bold text-emerald-700 ${isCurrentMonth ? '' : 'opacity-75'}`}>
            Total: {formatCurrency(dayTotal)}
          </div>
        )}
        {!isCurrentMonth && dayEntries.length === 0 && (
          <div className="text-xs text-slate-400 italic mt-2">
            {isPreviousMonth ? 'Previous month' : 'Next month'}
          </div>
        )}
      </div>
    );
  };

  const renderMonthlyCalendar = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    // Start from Monday of the week containing the first day
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - (firstDay.getDay() + 6) % 7); // Start from Monday

    const weeks = [];
    const currentWeekDate = new Date(startDate);

    // Generate 6 weeks to ensure we capture the full month view
    for (let weekNum = 0; weekNum < 6; weekNum++) {
      const week = [];
      for (let i = 0; i < 7; i++) {
        week.push(new Date(currentWeekDate));
        currentWeekDate.setDate(currentWeekDate.getDate() + 1);
      }
      weeks.push(week);
      
      // Stop if we've gone past the current month and captured at least one full week after
      if (weekNum > 0 && week[0].getMonth() !== month) {
        break;
      }
    }

    return (
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="grid grid-cols-7 bg-slate-50">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
            <div key={day} className="p-3 text-center font-semibold text-slate-700 border-r border-slate-200 last:border-r-0">
              {day}
            </div>
          ))}
        </div>
        {weeks.map((week, weekIndex) => (
          <div key={weekIndex} className="grid grid-cols-7">
            {week.map((date, dayIndex) => (
              <div key={dayIndex}>
                {renderCalendarDay(date)}
              </div>
            ))}
          </div>
        ))}
        
        {/* Legend for different month indicators */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-center space-x-6 text-xs text-slate-600">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-white border border-slate-300 rounded"></div>
            <span>Current Month</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-slate-100 border border-slate-300 rounded"></div>
            <span>Previous Month</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-slate-50 border border-slate-300 rounded"></div>
            <span>Next Month</span>
          </div>
        </div>
      </div>
    );
  };

  const { staffTotals, totalHours, totalPay } = getWeeklyTotals();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-slate-800 mb-2">Shift Roster & Pay Calculator</h1>
            <p className="text-slate-600">Professional workforce management system</p>
          </div>
          <div className="flex items-center space-x-4">
            <Badge variant="outline" className="px-3 py-1">
              {settings.pay_mode === 'default' ? 'Default Pay' : 'SCHADS Award'}
            </Badge>
            <Button
              variant="outline"
              onClick={() => setShowSettingsDialog(true)}
            >
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="roster" className="flex items-center space-x-2">
              <CalendarIcon className="w-4 h-4" />
              <span>Roster</span>
            </TabsTrigger>
            <TabsTrigger value="shifts" className="flex items-center space-x-2">
              <Clock className="w-4 h-4" />
              <span>Shift Times</span>
            </TabsTrigger>
            <TabsTrigger value="staff" className="flex items-center space-x-2">
              <Users className="w-4 h-4" />
              <span>Staff</span>
            </TabsTrigger>
            <TabsTrigger value="pay" className="flex items-center space-x-2">
              <DollarSign className="w-4 h-4" />
              <span>Pay Summary</span>
            </TabsTrigger>
            <TabsTrigger value="export" className="flex items-center space-x-2">
              <Download className="w-4 h-4" />
              <span>Export</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="roster" className="space-y-6">
            {/* Month Navigation */}
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <Button
                      variant="outline"
                      onClick={() => {
                        const newDate = new Date(currentDate);
                        newDate.setMonth(newDate.getMonth() - 1);
                        setCurrentDate(newDate);
                      }}
                    >
                      Previous Month
                    </Button>
                    <h2 className="text-2xl font-bold text-slate-800">
                      {currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                    </h2>
                    <Button
                      variant="outline"
                      onClick={() => {
                        const newDate = new Date(currentDate);
                        newDate.setMonth(newDate.getMonth() + 1);
                        setCurrentDate(newDate);
                      }}
                    >
                      Next Month
                    </Button>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button 
                      variant="outline"
                      onClick={() => {
                        setNewShift({
                          ...newShift,
                          date: currentDate.toISOString().split('T')[0]
                        });
                        setShowAddShiftDialog(true);
                      }}
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Add Shift
                    </Button>
                    <Button variant="outline" onClick={clearMonthlyRoster}>
                      Clear Roster
                    </Button>
                    <Button onClick={generateMonthlyRoster}>
                      Generate Roster
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Calendar */}
            {renderMonthlyCalendar()}
          </TabsContent>

          <TabsContent value="shifts" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Clock className="w-5 h-5" />
                  <span>Default Shift Times</span>
                </CardTitle>
                <p className="text-slate-600">
                  Adjust the default start and end times for each shift. These times will be used when generating new rosters.
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day, dayIndex) => {
                    const dayTemplates = shiftTemplates.filter(t => t.day_of_week === dayIndex);
                    return (
                      <div key={day} className="border rounded-lg p-4">
                        <h3 className="font-semibold text-lg mb-4">{day}</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                          {dayTemplates.map((template, shiftIndex) => (
                            <Card key={template.id} className="p-4">
                              <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                  <h4 className="font-medium">
                                    Shift {shiftIndex + 1}
                                    {template.is_sleepover && <Badge variant="secondary" className="ml-2">Sleepover</Badge>}
                                  </h4>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setSelectedTemplate(template);
                                      setShowTemplateDialog(true);
                                    }}
                                  >
                                    <Edit className="w-3 h-3 mr-1" />
                                    Edit
                                  </Button>
                                </div>
                                <div className="text-sm text-slate-600">
                                  {template.start_time} - {template.end_time}
                                </div>
                              </div>
                            </Card>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="staff" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center space-x-2">
                    <Users className="w-5 h-5" />
                    <span>Staff Management</span>
                  </CardTitle>
                  <Button onClick={() => setShowStaffDialog(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Staff
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {staff.map(member => (
                    <Card key={member.id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">{member.name}</h3>
                          <Badge variant={member.active ? "default" : "secondary"}>
                            {member.active ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="pay" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Clock className="w-5 h-5" />
                    <span>Total Hours</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-slate-800">{totalHours.toFixed(1)}</div>
                  <p className="text-slate-600">This week</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <DollarSign className="w-5 h-5" />
                    <span>Total Pay</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-emerald-600">{formatCurrency(totalPay)}</div>
                  <p className="text-slate-600">This week</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Users className="w-5 h-5" />
                    <span>Staff Count</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-slate-800">{staff.length}</div>
                  <p className="text-slate-600">Active staff</p>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Weekly Staff Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Staff Member</TableHead>
                      <TableHead>Hours Worked</TableHead>
                      <TableHead>Gross Pay</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(staffTotals).map(([name, totals]) => (
                      <TableRow key={name}>
                        <TableCell className="font-medium">{name}</TableCell>
                        <TableCell>{totals.hours.toFixed(1)}</TableCell>
                        <TableCell className="font-medium text-emerald-600">
                          {formatCurrency(totals.pay)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="export" className="space-y-6">
            <ExportManager baseUrl={API_BASE_URL} />
          </TabsContent>
        </Tabs>

        {/* Shift Assignment Dialog */}
        <Dialog open={showShiftDialog} onOpenChange={setShowShiftDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Edit Shift</DialogTitle>
            </DialogHeader>
            {selectedShift && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="start-time">Start Time</Label>
                    <Input
                      id="start-time"
                      type="time"
                      value={selectedShift.start_time}
                      onChange={(e) => {
                        setSelectedShift({
                          ...selectedShift,
                          start_time: e.target.value
                        });
                      }}
                    />
                  </div>
                  <div>
                    <Label htmlFor="end-time">End Time</Label>
                    <Input
                      id="end-time"
                      type="time"
                      value={selectedShift.end_time}
                      onChange={(e) => {
                        setSelectedShift({
                          ...selectedShift,
                          end_time: e.target.value
                        });
                      }}
                    />
                  </div>
                </div>
                
                <div className="text-sm text-slate-600">
                  Date: {new Date(selectedShift.date).toLocaleDateString()}
                </div>
                
                <div>
                  <Label htmlFor="staff-select">Assign Staff</Label>
                  <Select
                    value={selectedShift.staff_id || "unassigned"}
                    onValueChange={(staffId) => {
                      if (staffId === "unassigned") {
                        setSelectedShift({
                          ...selectedShift,
                          staff_id: null,
                          staff_name: null
                        });
                      } else {
                        const staff_member = staff.find(s => s.id === staffId);
                        const updatedShift = {
                          ...selectedShift,
                          staff_id: staffId,
                          staff_name: staff_member ? staff_member.name : null
                        };
                        setSelectedShift(updatedShift);
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select staff member" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="unassigned">Unassigned</SelectItem>
                      {staff.map(member => (
                        <SelectItem key={member.id} value={member.id}>
                          {member.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                <div className="space-y-3">
                  <h4 className="font-medium text-slate-700">Pay Calculation & Overrides</h4>
                  
                  <div className="flex items-center space-x-4 p-3 bg-blue-50 rounded-lg">
                    <Switch
                      checked={selectedShift.manual_sleepover !== null ? selectedShift.manual_sleepover : selectedShift.is_sleepover}
                      onCheckedChange={(checked) => {
                        setSelectedShift({
                          ...selectedShift,
                          manual_sleepover: checked,
                          manual_shift_type: checked ? 'sleepover' : null
                        });
                      }}
                    />
                    <div>
                      <Label className="font-medium">Sleepover Shift</Label>
                      <p className="text-xs text-slate-600">$175 flat rate includes 2 hours wake time</p>
                    </div>
                  </div>
                  
                  {(selectedShift.manual_sleepover || selectedShift.is_sleepover) && (
                    <div>
                      <Label htmlFor="wake-hours">Additional Wake Hours (beyond 2 hours)</Label>
                      <div className="flex items-center space-x-2">
                        <Input
                          id="wake-hours"
                          type="number"
                          step="0.5"
                          min="0"
                          max="8"
                          placeholder="0"
                          value={selectedShift.wake_hours || ''}
                          onChange={(e) => {
                            const wakeHours = parseFloat(e.target.value) || 0;
                            setSelectedShift({
                              ...selectedShift,
                              wake_hours: wakeHours
                            });
                          }}
                        />
                        <span className="text-sm text-slate-600">hours</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">Extra wake time paid at applicable hourly rate</p>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Shift Type Override</Label>
                      <Select
                        value={selectedShift.manual_shift_type || "auto"}
                        onValueChange={(value) => {
                          const manualType = value === "auto" ? null : value;
                          const isSleepover = value === "sleepover";
                          setSelectedShift({
                            ...selectedShift,
                            manual_shift_type: manualType,
                            manual_sleepover: isSleepover ? true : (manualType ? false : null)
                          });
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Auto-detect" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">Auto-detect</SelectItem>
                          <SelectItem value="weekday_day">Weekday Day ($42.00/hr)</SelectItem>
                          <SelectItem value="weekday_evening">Weekday Evening ($44.50/hr)</SelectItem>
                          <SelectItem value="weekday_night">Weekday Night ($48.50/hr)</SelectItem>
                          <SelectItem value="saturday">Saturday ($57.50/hr)</SelectItem>
                          <SelectItem value="sunday">Sunday ($74.00/hr)</SelectItem>
                          <SelectItem value="public_holiday">Public Holiday ($88.50/hr)</SelectItem>
                          <SelectItem value="sleepover">Sleepover ($175 + extra wake hours)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Custom Hourly Rate</Label>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm">$</span>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          placeholder="Auto-calculated"
                          value={selectedShift.manual_hourly_rate || ''}
                          onChange={(e) => {
                            const manualRate = parseFloat(e.target.value) || null;
                            setSelectedShift({
                              ...selectedShift,
                              manual_hourly_rate: manualRate
                            });
                          }}
                        />
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Hours Worked</Label>
                      <div className="text-lg font-medium">{selectedShift.hours_worked.toFixed(1)}</div>
                    </div>
                    <div>
                      <Label>Current Shift Type</Label>
                      {getShiftTypeBadge(selectedShift)}
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="manual-base-pay">Base Pay Override</Label>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm">$</span>
                        <Input
                          id="manual-base-pay"
                          type="number"
                          step="0.01"
                          min="0"
                          placeholder="Auto-calculated"
                          onChange={(e) => {
                            const manualPay = parseFloat(e.target.value) || null;
                            setSelectedShift({
                              ...selectedShift,
                              manual_base_pay: manualPay,
                              total_pay: (manualPay || selectedShift.base_pay) + selectedShift.sleepover_allowance
                            });
                          }}
                        />
                      </div>
                      <p className="text-xs text-slate-500 mt-1">Leave empty for auto-calculation</p>
                    </div>
                    <div>
                      <Label>Sleepover Allowance</Label>
                      <div className="text-lg font-medium">
                        {selectedShift.sleepover_allowance > 0 ? formatCurrency(selectedShift.sleepover_allowance) : '-'}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-2 bg-slate-50 p-3 rounded-lg">
                  <div className="flex justify-between text-sm">
                    <span>Calculated Base Pay:</span>
                    <span className="font-medium">{formatCurrency(selectedShift.base_pay)}</span>
                  </div>
                  {selectedShift.sleepover_allowance > 0 && (
                    <div className="flex justify-between text-sm">
                      <span>Sleepover Allowance:</span>
                      <span className="font-medium">{formatCurrency(selectedShift.sleepover_allowance)}</span>
                    </div>
                  )}
                  <Separator />
                  <div className="flex justify-between font-bold">
                    <span>Total Pay:</span>
                    <span className="text-emerald-600">{formatCurrency(selectedShift.total_pay)}</span>
                  </div>
                </div>

                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setShowShiftDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={() => {
                    // Include all manual overrides in the update
                    const updates = {
                      staff_id: selectedShift.staff_id,
                      staff_name: selectedShift.staff_name,
                      start_time: selectedShift.start_time,
                      end_time: selectedShift.end_time,
                      manual_shift_type: selectedShift.manual_shift_type || null,
                      manual_hourly_rate: selectedShift.manual_hourly_rate || null,
                      manual_sleepover: selectedShift.manual_sleepover,
                      wake_hours: selectedShift.wake_hours || null
                    };
                    
                    console.log('Saving shift with updates:', updates);
                    updateRosterEntry(selectedShift.id, updates);
                    setShowShiftDialog(false);
                  }}>
                    Save Changes
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Add Shift Dialog */}
        <Dialog open={showAddShiftDialog} onOpenChange={setShowAddShiftDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Add New Shift</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="shift-date">Date</Label>
                <Input
                  id="shift-date"
                  type="date"
                  value={newShift.date}
                  onChange={(e) => setNewShift({...newShift, date: e.target.value})}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="shift-start">Start Time</Label>
                  <Input
                    id="shift-start"
                    type="time"
                    value={newShift.start_time}
                    onChange={(e) => setNewShift({...newShift, start_time: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="shift-end">End Time</Label>
                  <Input
                    id="shift-end"
                    type="time"
                    value={newShift.end_time}
                    onChange={(e) => setNewShift({...newShift, end_time: e.target.value})}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  checked={newShift.is_sleepover}
                  onCheckedChange={(checked) => setNewShift({...newShift, is_sleepover: checked})}
                />
                <Label>Sleepover Shift</Label>
              </div>

              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setShowAddShiftDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={addIndividualShift}>
                  Add Shift
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Break Warning Dialog */}
        <Dialog open={showBreakWarning} onOpenChange={setShowBreakWarning}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2 text-amber-600">
                <Clock className="w-5 h-5" />
                <span>Shift Break Warning</span>
              </DialogTitle>
            </DialogHeader>
            {breakWarningData && (
              <div className="space-y-4">
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center">
                        <Clock className="w-4 h-4 text-amber-600" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-amber-800 mb-1">
                        Insufficient Break Time
                      </h3>
                      <p className="text-sm text-amber-700 mb-2">
                        {breakWarningData.violation.message}
                      </p>
                      <div className="text-xs text-amber-600">
                        <strong>Shift Sequence:</strong><br />
                        {breakWarningData.violation.details}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="text-sm text-slate-600 space-y-2">
                  <p><strong>Policy:</strong> Staff must have at least 10 hours break between shifts.</p>
                  <p><strong>Exceptions:</strong> Sleepover shifts are exempt from this rule.</p>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg">
                  <p className="text-sm font-medium text-slate-700 mb-1">Do you want to proceed?</p>
                  <p className="text-xs text-slate-600">
                    Approving this assignment may violate workplace safety regulations.
                  </p>
                </div>

                <div className="flex justify-end space-x-3">
                  <Button 
                    variant="outline" 
                    onClick={denyShiftAssignment}
                    className="border-amber-300 text-amber-700 hover:bg-amber-50"
                  >
                    Deny Assignment
                  </Button>
                  <Button 
                    onClick={approveShiftAssignment}
                    className="bg-amber-600 hover:bg-amber-700 text-white"
                  >
                    Approve Override
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Shift Template Edit Dialog */}
        <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Edit Default Shift Time</DialogTitle>
            </DialogHeader>
            {selectedTemplate && (
              <div className="space-y-4">
                <div>
                  <Label>Shift</Label>
                  <div className="text-sm text-slate-600 mb-2">
                    {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][selectedTemplate.day_of_week]} - 
                    {selectedTemplate.name}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="template-start-time">Start Time</Label>
                    <Input
                      id="template-start-time"
                      type="time"
                      value={selectedTemplate.start_time}
                      onChange={(e) => {
                        setSelectedTemplate({
                          ...selectedTemplate,
                          start_time: e.target.value
                        });
                      }}
                    />
                  </div>
                  <div>
                    <Label htmlFor="template-end-time">End Time</Label>
                    <Input
                      id="template-end-time"
                      type="time"
                      value={selectedTemplate.end_time}
                      onChange={(e) => {
                        setSelectedTemplate({
                          ...selectedTemplate,
                          end_time: e.target.value
                        });
                      }}
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    checked={selectedTemplate.is_sleepover}
                    onCheckedChange={(checked) => {
                      setSelectedTemplate({
                        ...selectedTemplate,
                        is_sleepover: checked
                      });
                    }}
                  />
                  <Label>Sleepover Shift</Label>
                </div>

                <div className="text-sm text-slate-600 p-3 bg-slate-50 rounded-lg">
                  <strong>Note:</strong> Changes to default shift times will only affect newly generated rosters. 
                  Existing roster entries can be edited individually.
                </div>

                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setShowTemplateDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={() => {
                    updateShiftTemplate(selectedTemplate.id, {
                      start_time: selectedTemplate.start_time,
                      end_time: selectedTemplate.end_time,
                      is_sleepover: selectedTemplate.is_sleepover
                    });
                    setShowTemplateDialog(false);
                  }}>
                    Save Changes
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Add Staff Dialog */}
        <Dialog open={showStaffDialog} onOpenChange={setShowStaffDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Add New Staff Member</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="staff-name">Name</Label>
                <Input
                  id="staff-name"
                  value={newStaffName}
                  onChange={(e) => setNewStaffName(e.target.value)}
                  placeholder="Enter staff name"
                />
              </div>
              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setShowStaffDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={addStaff}>Add Staff</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Settings Dialog */}
        <Dialog open={showSettingsDialog} onOpenChange={setShowSettingsDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Settings</DialogTitle>
            </DialogHeader>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-medium">Pay Mode</Label>
                  <p className="text-sm text-slate-600">Switch between Default rates and SCHADS Award compliance</p>
                </div>
                <Switch
                  checked={settings.pay_mode === 'schads'}
                  onCheckedChange={(checked) => {
                    const newSettings = {
                      ...settings,
                      pay_mode: checked ? 'schads' : 'default'
                    };
                    updateSettings(newSettings);
                  }}
                />
              </div>

              <Separator />

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Pay Rates (Per Hour)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Weekday Day Rate (6am-8pm)</Label>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm">$</span>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={settings.rates.weekday_day}
                        onChange={(e) => {
                          const newSettings = {
                            ...settings,
                            rates: {
                              ...settings.rates,
                              weekday_day: parseFloat(e.target.value) || 0
                            }
                          };
                          setSettings(newSettings);
                        }}
                      />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Starts at/after 6:00am, ends at/before 8:00pm</p>
                  </div>
                  <div>
                    <Label>Weekday Evening Rate (after 8pm)</Label>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm">$</span>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={settings.rates.weekday_evening}
                        onChange={(e) => {
                          const newSettings = {
                            ...settings,
                            rates: {
                              ...settings.rates,
                              weekday_evening: parseFloat(e.target.value) || 0
                            }
                          };
                          setSettings(newSettings);
                        }}
                      />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Starts after 8:00pm OR extends past 8:00pm</p>
                  </div>
                  <div>
                    <Label>Weekday Night Rate (overnight)</Label>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm">$</span>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={settings.rates.weekday_night}
                        onChange={(e) => {
                          const newSettings = {
                            ...settings,
                            rates: {
                              ...settings.rates,
                              weekday_night: parseFloat(e.target.value) || 0
                            }
                          };
                          setSettings(newSettings);
                        }}
                      />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Commences at/before midnight and finishes after midnight</p>
                  </div>
                  <div>
                    <Label>Saturday Rate (all hours)</Label>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm">$</span>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={settings.rates.saturday}
                        onChange={(e) => {
                          const newSettings = {
                            ...settings,
                            rates: {
                              ...settings.rates,
                              saturday: parseFloat(e.target.value) || 0
                            }
                          };
                          setSettings(newSettings);
                        }}
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Sunday Rate (all hours)</Label>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm">$</span>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={settings.rates.sunday}
                        onChange={(e) => {
                          const newSettings = {
                            ...settings,
                            rates: {
                              ...settings.rates,
                              sunday: parseFloat(e.target.value) || 0
                            }
                          };
                          setSettings(newSettings);
                        }}
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Public Holiday Rate (all hours)</Label>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm">$</span>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={settings.rates.public_holiday}
                        onChange={(e) => {
                          const newSettings = {
                            ...settings,
                            rates: {
                              ...settings.rates,
                              public_holiday: parseFloat(e.target.value) || 0
                            }
                          };
                          setSettings(newSettings);
                        }}
                      />
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Sleepover Allowances</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label>Sleepover Allowance (Default)</Label>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm">$</span>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={settings.rates.sleepover_default}
                          onChange={(e) => {
                            const newSettings = {
                              ...settings,
                              rates: {
                                ...settings.rates,
                                sleepover_default: parseFloat(e.target.value) || 0
                              }
                            };
                            setSettings(newSettings);
                          }}
                        />
                      </div>
                      <p className="text-xs text-slate-500 mt-1">$175 per night includes 2 hours wake time</p>
                    </div>
                    <div>
                      <Label>Sleepover Allowance (SCHADS)</Label>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm">$</span>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={settings.rates.sleepover_schads}
                          onChange={(e) => {
                            const newSettings = {
                              ...settings,
                              rates: {
                                ...settings.rates,
                                sleepover_schads: parseFloat(e.target.value) || 0
                              }
                            };
                            setSettings(newSettings);
                          }}
                        />
                      </div>
                      <p className="text-xs text-slate-500 mt-1">SCHADS Award compliant rate</p>
                    </div>
                  </div>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="text-sm font-semibold text-blue-800 mb-2">SCHADS Award Rules:</h4>
                  <ul className="text-xs text-blue-700 space-y-1">
                    <li>• <strong>Day:</strong> Starts at/after 6:00am and ends at/before 8:00pm</li>
                    <li>• <strong>Evening:</strong> Starts after 8:00pm OR any shift that extends past 8:00pm</li>
                    <li>• <strong>Night:</strong> Commences at/before midnight and finishes after midnight</li>
                    <li>• <strong>Sleepover:</strong> $175 includes 2 hours wake time, additional at hourly rate</li>
                  </ul>
                </div>
              </div>

              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setShowSettingsDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={() => updateSettings(settings)}>
                  Save Settings
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

export default App;
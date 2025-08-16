"""
Export Services for Workforce Management System
Handles PDF, Excel, and CSV export functionality
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
import pandas as pd
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import logging

logger = logging.getLogger(__name__)


class ExportService:
    """Service class for handling export data operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_shift_roster_data(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve shift roster data with optional filters"""
        try:
            # Build query filters
            query = {}
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date.isoformat()
                if end_date:
                    date_filter["$lte"] = end_date.isoformat()
                query["shift_date"] = date_filter
            
            if department:
                # Find staff in the specified department first
                staff_cursor = self.db.staff.find({"department": department})
                staff_list = await staff_cursor.to_list(None)
                staff_names = [staff["name"] for staff in staff_list]
                if staff_names:
                    query["staff_member"] = {"$in": staff_names}
                else:
                    # No staff in department, return empty
                    return []
            
            # Fetch roster data
            cursor = self.db.roster.find(query)
            roster_data = await cursor.to_list(None)
            
            # Enrich with staff details
            enriched_data = []
            for entry in roster_data:
                # Get staff details
                staff = await self.db.staff.find_one({"name": entry.get("staff_member")})
                
                enriched_entry = {
                    "employee_id": staff.get("id", "") if staff else "",
                    "employee_name": entry.get("staff_member", ""),
                    "shift_date": entry.get("shift_date", ""),
                    "start_time": entry.get("start_time", ""),
                    "end_time": entry.get("end_time", ""),
                    "position": staff.get("position", "") if staff else "",
                    "department": staff.get("department", "") if staff else "",
                    "status": "completed",  # Default status
                    "hours_worked": entry.get("total_hours", 0),
                    "shift_type": entry.get("shift_type", ""),
                    "regular_hours": entry.get("regular_hours", 0),
                    "evening_hours": entry.get("evening_hours", 0),
                    "night_hours": entry.get("night_hours", 0),
                    "saturday_hours": entry.get("saturday_hours", 0),
                    "sunday_hours": entry.get("sunday_hours", 0),
                    "public_holiday_hours": entry.get("public_holiday_hours", 0),
                    "sleepover_allowance": entry.get("sleepover_allowance", 0),
                    "total_pay": entry.get("total_pay", 0)
                }
                enriched_data.append(enriched_entry)
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"Error retrieving shift roster data: {str(e)}")
            raise
    
    async def get_pay_summary_data(
        self,
        pay_period_start: Optional[date] = None,
        pay_period_end: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve pay summary data with optional filters"""
        try:
            # Build query filters
            query = {}
            
            if pay_period_start or pay_period_end:
                date_filter = {}
                if pay_period_start:
                    date_filter["$gte"] = pay_period_start.isoformat()
                if pay_period_end:
                    date_filter["$lte"] = pay_period_end.isoformat()
                query["shift_date"] = date_filter
            
            # Fetch roster data and aggregate by staff member
            cursor = self.db.roster.find(query)
            roster_data = await cursor.to_list(None)
            
            # Group by staff member and calculate totals
            staff_totals = {}
            
            for entry in roster_data:
                staff_name = entry.get("staff_member", "")
                if staff_name not in staff_totals:
                    staff_totals[staff_name] = {
                        "regular_hours": 0,
                        "overtime_hours": 0,  # We don't track overtime separately yet
                        "evening_hours": 0,
                        "night_hours": 0,
                        "saturday_hours": 0,
                        "sunday_hours": 0,
                        "public_holiday_hours": 0,
                        "total_pay": 0,
                        "shift_count": 0
                    }
                
                staff_totals[staff_name]["regular_hours"] += entry.get("regular_hours", 0)
                staff_totals[staff_name]["evening_hours"] += entry.get("evening_hours", 0)
                staff_totals[staff_name]["night_hours"] += entry.get("night_hours", 0)
                staff_totals[staff_name]["saturday_hours"] += entry.get("saturday_hours", 0)
                staff_totals[staff_name]["sunday_hours"] += entry.get("sunday_hours", 0)
                staff_totals[staff_name]["public_holiday_hours"] += entry.get("public_holiday_hours", 0)
                staff_totals[staff_name]["total_pay"] += entry.get("total_pay", 0)
                staff_totals[staff_name]["shift_count"] += 1
            
            # Format pay summary data
            pay_summary = []
            for staff_name, totals in staff_totals.items():
                # Get staff details
                staff = await self.db.staff.find_one({"name": staff_name})
                
                total_hours = (
                    totals["regular_hours"] + totals["evening_hours"] + 
                    totals["night_hours"] + totals["saturday_hours"] + 
                    totals["sunday_hours"] + totals["public_holiday_hours"]
                )
                
                pay_entry = {
                    "employee_id": staff.get("id", "") if staff else "",
                    "employee_name": staff_name,
                    "pay_period_start": pay_period_start.isoformat() if pay_period_start else "",
                    "pay_period_end": pay_period_end.isoformat() if pay_period_end else "",
                    "regular_hours": totals["regular_hours"],
                    "evening_hours": totals["evening_hours"],
                    "night_hours": totals["night_hours"],
                    "saturday_hours": totals["saturday_hours"],
                    "sunday_hours": totals["sunday_hours"],
                    "public_holiday_hours": totals["public_holiday_hours"],
                    "total_hours": total_hours,
                    "overtime_hours": max(0, total_hours - 38),  # Assume 38 hour standard week
                    "regular_rate": 42.00,  # Base SCHADS rate
                    "overtime_rate": 63.00,  # 1.5x overtime rate
                    "gross_pay": totals["total_pay"],
                    "deductions": totals["total_pay"] * 0.15,  # Assume 15% deductions
                    "net_pay": totals["total_pay"] * 0.85,  # Net after deductions
                    "shift_count": totals["shift_count"]
                }
                pay_summary.append(pay_entry)
            
            return pay_summary
            
        except Exception as e:
            logger.error(f"Error retrieving pay summary data: {str(e)}")
            raise
    
    async def get_workforce_data(self) -> List[Dict[str, Any]]:
        """Retrieve comprehensive workforce data"""
        try:
            # Get all staff
            cursor = self.db.staff.find({"active": True})
            staff_data = await cursor.to_list(None)
            
            workforce_data = []
            for staff in staff_data:
                workforce_entry = {
                    "employee_id": staff.get("id", ""),
                    "full_name": staff.get("name", ""),
                    "email": staff.get("email", ""),
                    "phone": staff.get("phone", ""),
                    "department": staff.get("department", ""),
                    "position": staff.get("position", ""),
                    "hire_date": staff.get("hire_date", ""),
                    "employment_status": "Active" if staff.get("active", True) else "Inactive",
                    "manager_name": staff.get("manager", ""),
                    "hourly_rate": staff.get("hourly_rate", 42.00)
                }
                workforce_data.append(workforce_entry)
            
            return workforce_data
            
        except Exception as e:
            logger.error(f"Error retrieving workforce data: {str(e)}")
            raise
    
    def generate_csv_content(self, data: List[Dict[str, Any]]) -> str:
        """Generate CSV content from data"""
        if not data:
            return ""
        
        try:
            df = pd.DataFrame(data)
            
            # Format currency and numeric columns
            for col in df.columns:
                if 'pay' in col.lower() or 'rate' in col.lower() or 'deduction' in col.lower():
                    df[col] = df[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x != "" else "$0.00")
                elif 'hours' in col.lower():
                    df[col] = df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) and x != "" else "0.0")
            
            return df.to_csv(index=False)
            
        except Exception as e:
            logger.error(f"Error generating CSV content: {str(e)}")
            raise
    
    def generate_excel_content(self, data_sheets: Dict[str, List[Dict[str, Any]]]) -> bytes:
        """Generate Excel content with multiple sheets"""
        try:
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                for sheet_name, data in data_sheets.items():
                    if not data:
                        continue
                    
                    df = pd.DataFrame(data)
                    
                    # Format currency and numeric columns
                    for col in df.columns:
                        if 'pay' in col.lower() or 'rate' in col.lower() or 'deduction' in col.lower():
                            df[col] = df[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) and x != "" else "$0.00")
                        elif 'hours' in col.lower():
                            df[col] = df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) and x != "" else "0.0")
                    
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Apply formatting
                    workbook = writer.book
                    worksheet = workbook[sheet_name]
                    
                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                    
                    # Style headers
                    from openpyxl.styles import Font, PatternFill
                    header_font = Font(bold=True, color="FFFFFF")
                    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                    
                    for cell in worksheet[1]:
                        cell.font = header_font
                        cell.fill = header_fill
            
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating Excel content: {str(e)}")
            raise
    
    def generate_pdf_content(self, title: str, data: List[Dict[str, Any]]) -> bytes:
        """Generate PDF content for reports"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            
            # Build story (content) for PDF
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            
            title_para = Paragraph(title, title_style)
            story.append(title_para)
            story.append(Spacer(1, 20))
            
            if not data:
                no_data_para = Paragraph("No data available for the selected criteria.", styles['Normal'])
                story.append(no_data_para)
            else:
                # Create table data
                if data:
                    # Get column headers
                    headers = list(data[0].keys())
                    table_data = [headers]
                    
                    # Add data rows
                    for item in data[:50]:  # Limit to first 50 rows for PDF
                        row = []
                        for header in headers:
                            value = item.get(header, "")
                            if isinstance(value, (int, float)) and ('pay' in header.lower() or 'rate' in header.lower()):
                                row.append(f"${value:.2f}")
                            elif isinstance(value, float) and 'hours' in header.lower():
                                row.append(f"{value:.1f}")
                            else:
                                row.append(str(value))
                        table_data.append(row)
                    
                    # Create table
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ]))
                    
                    story.append(table)
                    
                    # Add summary if more than 50 records
                    if len(data) > 50:
                        story.append(Spacer(1, 20))
                        summary_para = Paragraph(
                            f"Note: This report shows the first 50 records out of {len(data)} total records.",
                            styles['Italic']
                        )
                        story.append(summary_para)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating PDF content: {str(e)}")
            raise


class HolidayService:
    """Service for Queensland public holiday detection"""
    
    def __init__(self):
        import holidays
        # Initialize Queensland holidays
        self.qld_holidays = holidays.Australia(subdiv='QLD')
    
    def is_public_holiday(self, check_date: date, location: str = "QLD") -> bool:
        """Check if a date is a Queensland public holiday"""
        try:
            # For Brisbane-specific holidays like Royal Queensland Show
            if location.upper() in ["BRISBANE", "BNE"]:
                # Brisbane gets all QLD holidays including Royal Queensland Show
                return check_date in self.qld_holidays
            else:
                # Other QLD locations - check if it's a non-Brisbane specific holiday
                holiday_name = self.qld_holidays.get(check_date, "")
                # Royal Queensland Show is Brisbane-only
                if "royal queensland show" in holiday_name.lower():
                    return False
                return check_date in self.qld_holidays
                
        except Exception as e:
            logger.error(f"Error checking public holiday: {str(e)}")
            return False
    
    def get_holiday_name(self, check_date: date) -> str:
        """Get the name of the public holiday"""
        try:
            return self.qld_holidays.get(check_date, "")
        except Exception as e:
            logger.error(f"Error getting holiday name: {str(e)}")
            return ""
    
    def get_holidays_in_range(self, start_date: date, end_date: date, location: str = "QLD") -> List[Dict[str, Any]]:
        """Get all holidays in a date range"""
        try:
            holidays_list = []
            current_date = start_date
            
            while current_date <= end_date:
                if self.is_public_holiday(current_date, location):
                    holiday_name = self.get_holiday_name(current_date)
                    holidays_list.append({
                        "date": current_date.isoformat(),
                        "name": holiday_name,
                        "location": location
                    })
                current_date = current_date.replace(day=current_date.day + 1)
            
            return holidays_list
            
        except Exception as e:
            logger.error(f"Error getting holidays in range: {str(e)}")
            return []
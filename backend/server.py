from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, time, timedelta, date
import os
import uuid
from enum import Enum
import io
from export_services import ExportService, HolidayService

# Database setup
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "shift_roster_db")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Async motor client for export services
motor_client = AsyncIOMotorClient(MONGO_URL)
motor_db = motor_client[DB_NAME]

# Initialize services
export_service = ExportService(motor_db)
holiday_service = HolidayService()

app = FastAPI(title="Shift Roster & Pay Calculator")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class PayMode(str, Enum):
    DEFAULT = "default"
    SCHADS = "schads"

class ShiftType(str, Enum):
    WEEKDAY_DAY = "weekday_day"
    WEEKDAY_EVENING = "weekday_evening"
    WEEKDAY_NIGHT = "weekday_night"
    SATURDAY = "saturday"
    SUNDAY = "sunday"
    PUBLIC_HOLIDAY = "public_holiday"
    SLEEPOVER = "sleepover"

# Pydantic models
class Staff(BaseModel):
    id: str
    name: str
    active: bool = True
    created_at: datetime = None

class ShiftTemplate(BaseModel):
    id: str
    name: str
    start_time: str
    end_time: str
    is_sleepover: bool = False
    day_of_week: int  # 0=Monday, 6=Sunday

class RosterEntry(BaseModel):
    id: str
    date: str  # YYYY-MM-DD
    shift_template_id: str
    staff_id: Optional[str] = None
    staff_name: Optional[str] = None
    start_time: str
    end_time: str
    is_sleepover: bool = False
    is_public_holiday: bool = False
    manual_shift_type: Optional[str] = None  # Manual override for shift type
    manual_hourly_rate: Optional[float] = None  # Manual override for hourly rate
    manual_sleepover: Optional[bool] = None  # Manual override for sleepover status
    wake_hours: Optional[float] = None  # Additional wake hours beyond 2 hours
    hours_worked: float = 0.0
    base_pay: float = 0.0
    sleepover_allowance: float = 0.0
    total_pay: float = 0.0

class Settings(BaseModel):
    pay_mode: PayMode = PayMode.DEFAULT
    rates: Dict[str, float] = {
        "weekday_day": 42.00,
        "weekday_evening": 44.50,
        "weekday_night": 48.50,
        "saturday": 57.50,
        "sunday": 74.00,
        "public_holiday": 88.50,
        "sleepover_default": 175.00,
        "sleepover_schads": 60.02
    }

# Pay calculation functions
def determine_shift_type(date_str: str, start_time: str, end_time: str, is_public_holiday: bool) -> ShiftType:
    """Determine the shift type based on date and time - SIMPLIFIED LOGIC"""
    
    if is_public_holiday:
        return ShiftType.PUBLIC_HOLIDAY
    
    # Parse date and get day of week
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    day_of_week = date_obj.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday
    
    # Weekend rates override time-based logic
    if day_of_week == 5:  # Saturday
        return ShiftType.SATURDAY
    elif day_of_week == 6:  # Sunday
        return ShiftType.SUNDAY
    
    # For weekdays (Monday-Friday), check time ranges
    start_hour = int(start_time.split(":")[0])
    start_min = int(start_time.split(":")[1])
    end_hour = int(end_time.split(":")[0])
    end_min = int(end_time.split(":")[1])
    
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min
    
    # Handle overnight shifts
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
    
    # Simple time-based classification for weekdays
    # Night: starts before 6am OR ends after midnight
    if start_hour < 6 or end_minutes > 24 * 60:
        return ShiftType.WEEKDAY_NIGHT
    # Evening: starts at 8pm or later OR extends past 8pm
    elif start_hour >= 20 or end_minutes > 20 * 60:
        return ShiftType.WEEKDAY_EVENING
    # Day: everything else (6am-8pm range)
    else:
        return ShiftType.WEEKDAY_DAY

def calculate_hours_worked(start_time: str, end_time: str) -> float:
    """Calculate hours worked between start and end time"""
    start_hour, start_min = map(int, start_time.split(":"))
    end_hour, end_min = map(int, end_time.split(":"))
    
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min
    
    # Handle overnight shifts
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
    
    total_minutes = end_minutes - start_minutes
    return total_minutes / 60.0

def calculate_pay(roster_entry: RosterEntry, settings: Settings) -> RosterEntry:
    """Calculate pay for a roster entry with sleepover logic and Queensland public holiday detection"""
    hours = calculate_hours_worked(roster_entry.start_time, roster_entry.end_time)
    roster_entry.hours_worked = hours
    
    # Check if this date is a Queensland public holiday (unless manually overridden)
    if not roster_entry.manual_shift_type and not roster_entry.is_public_holiday:
        try:
            date_obj = datetime.strptime(roster_entry.date, "%Y-%m-%d").date()
            # Default to QLD for now - could be enhanced with staff location data
            roster_entry.is_public_holiday = holiday_service.is_public_holiday(date_obj, "QLD")
        except Exception as e:
            print(f"Error checking public holiday for {roster_entry.date}: {e}")
            roster_entry.is_public_holiday = False
    
    # Determine if this is a sleepover shift
    is_sleepover = roster_entry.manual_sleepover if roster_entry.manual_sleepover is not None else roster_entry.is_sleepover
    
    if is_sleepover:
        # Sleepover calculation: $175 flat rate includes 2 hours
        roster_entry.sleepover_allowance = 175.00  # Fixed $175 per night
        
        # Additional wake hours beyond 2 hours at applicable hourly rate
        wake_hours = roster_entry.wake_hours if roster_entry.wake_hours else 0
        extra_wake_hours = max(0, wake_hours - 2) if wake_hours > 2 else 0
        
        if extra_wake_hours > 0:
            # Get applicable hourly rate for extra wake time
            if roster_entry.manual_hourly_rate:
                hourly_rate = roster_entry.manual_hourly_rate
            else:
                # Determine rate based on shift type or manual override
                if roster_entry.manual_shift_type:
                    shift_type_map = {
                        "weekday_day": ShiftType.WEEKDAY_DAY,
                        "weekday_evening": ShiftType.WEEKDAY_EVENING,
                        "weekday_night": ShiftType.WEEKDAY_NIGHT,
                        "saturday": ShiftType.SATURDAY,
                        "sunday": ShiftType.SUNDAY,
                        "public_holiday": ShiftType.PUBLIC_HOLIDAY
                    }
                    shift_type = shift_type_map.get(roster_entry.manual_shift_type, ShiftType.WEEKDAY_DAY)
                else:
                    shift_type = determine_shift_type(
                        roster_entry.date, 
                        roster_entry.start_time, 
                        roster_entry.end_time,
                        roster_entry.is_public_holiday
                    )
                
                # Get hourly rate based on shift type
                if shift_type == ShiftType.PUBLIC_HOLIDAY:
                    hourly_rate = settings.rates["public_holiday"]
                elif shift_type == ShiftType.SATURDAY:
                    hourly_rate = settings.rates["saturday"]
                elif shift_type == ShiftType.SUNDAY:
                    hourly_rate = settings.rates["sunday"]
                elif shift_type == ShiftType.WEEKDAY_EVENING:
                    hourly_rate = settings.rates["weekday_evening"]
                elif shift_type == ShiftType.WEEKDAY_NIGHT:
                    hourly_rate = settings.rates["weekday_night"]
                else:
                    hourly_rate = settings.rates["weekday_day"]
            
            roster_entry.base_pay = extra_wake_hours * hourly_rate
        else:
            roster_entry.base_pay = 0  # Only sleepover allowance
            
    else:
        # Regular shift calculation
        roster_entry.sleepover_allowance = 0
        
        # Use manual hourly rate if provided
        if roster_entry.manual_hourly_rate:
            hourly_rate = roster_entry.manual_hourly_rate
        else:
            # Use manual shift type if provided, otherwise determine automatically
            if roster_entry.manual_shift_type:
                shift_type_map = {
                    "weekday_day": ShiftType.WEEKDAY_DAY,
                    "weekday_evening": ShiftType.WEEKDAY_EVENING,
                    "weekday_night": ShiftType.WEEKDAY_NIGHT,
                    "saturday": ShiftType.SATURDAY,
                    "sunday": ShiftType.SUNDAY,
                    "public_holiday": ShiftType.PUBLIC_HOLIDAY
                }
                shift_type = shift_type_map.get(roster_entry.manual_shift_type, ShiftType.WEEKDAY_DAY)
            else:
                # Determine shift type automatically
                shift_type = determine_shift_type(
                    roster_entry.date, 
                    roster_entry.start_time, 
                    roster_entry.end_time,
                    roster_entry.is_public_holiday
                )
            
            # Get hourly rate based on shift type - Queensland public holiday integration
            if shift_type == ShiftType.PUBLIC_HOLIDAY:
                hourly_rate = settings.rates["public_holiday"]  # $88.50/hr for QLD public holidays
            elif shift_type == ShiftType.SATURDAY:
                hourly_rate = settings.rates["saturday"]
            elif shift_type == ShiftType.SUNDAY:
                hourly_rate = settings.rates["sunday"]
            elif shift_type == ShiftType.WEEKDAY_EVENING:
                hourly_rate = settings.rates["weekday_evening"]
            elif shift_type == ShiftType.WEEKDAY_NIGHT:
                hourly_rate = settings.rates["weekday_night"]
            else:
                hourly_rate = settings.rates["weekday_day"]
        
        roster_entry.base_pay = hours * hourly_rate
    
    roster_entry.total_pay = roster_entry.base_pay + roster_entry.sleepover_allowance
    return roster_entry

# Initialize default data
def initialize_default_data():
    """Initialize default staff and shift templates"""
    
    # Default staff members
    default_staff = [
        "Angela", "Chanelle", "Rose", "Caroline", "Nox", "Elina",
        "Kayla", "Rhet", "Nikita", "Molly", "Felicity", "Issey"
    ]
    
    for staff_name in default_staff:
        existing = db.staff.find_one({"name": staff_name})
        if not existing:
            staff = Staff(
                id=str(uuid.uuid4()),
                name=staff_name,
                active=True,
                created_at=datetime.now()
            )
            db.staff.insert_one(staff.dict())
    
    # Clear existing shift templates and create new ones per user requirements
    db.shift_templates.delete_many({})
    
    # Updated shift templates according to user specifications
    shift_templates = [
        # Monday
        {"name": "Monday Shift 1", "start_time": "07:30", "end_time": "15:30", "is_sleepover": False, "day_of_week": 0},  # Weekday Day
        {"name": "Monday Shift 2", "start_time": "15:00", "end_time": "20:00", "is_sleepover": False, "day_of_week": 0},  # Weekday Day  
        {"name": "Monday Shift 3", "start_time": "15:30", "end_time": "23:30", "is_sleepover": False, "day_of_week": 0},  # Weekday Evening
        {"name": "Monday Shift 4", "start_time": "23:30", "end_time": "07:30", "is_sleepover": True, "day_of_week": 0},   # Sleepover
        
        # Tuesday
        {"name": "Tuesday Shift 1", "start_time": "07:30", "end_time": "15:30", "is_sleepover": False, "day_of_week": 1},  # Weekday Day
        {"name": "Tuesday Shift 2", "start_time": "12:00", "end_time": "20:00", "is_sleepover": False, "day_of_week": 1},  # Weekday Day
        {"name": "Tuesday Shift 3", "start_time": "15:30", "end_time": "23:30", "is_sleepover": False, "day_of_week": 1},  # Weekday Evening
        {"name": "Tuesday Shift 4", "start_time": "23:30", "end_time": "07:30", "is_sleepover": True, "day_of_week": 1},   # Sleepover
        
        # Wednesday
        {"name": "Wednesday Shift 1", "start_time": "07:30", "end_time": "15:30", "is_sleepover": False, "day_of_week": 2},  # Weekday Day
        {"name": "Wednesday Shift 2", "start_time": "15:00", "end_time": "20:00", "is_sleepover": False, "day_of_week": 2},  # Weekday Day
        {"name": "Wednesday Shift 3", "start_time": "15:30", "end_time": "23:30", "is_sleepover": False, "day_of_week": 2},  # Weekday Evening
        {"name": "Wednesday Shift 4", "start_time": "23:30", "end_time": "07:30", "is_sleepover": True, "day_of_week": 2},   # Sleepover
        
        # Thursday
        {"name": "Thursday Shift 1", "start_time": "07:30", "end_time": "15:30", "is_sleepover": False, "day_of_week": 3},  # Weekday Day
        {"name": "Thursday Shift 2", "start_time": "12:00", "end_time": "20:00", "is_sleepover": False, "day_of_week": 3},  # Weekday Day
        {"name": "Thursday Shift 3", "start_time": "15:30", "end_time": "23:30", "is_sleepover": False, "day_of_week": 3},  # Weekday Evening
        {"name": "Thursday Shift 4", "start_time": "23:30", "end_time": "07:30", "is_sleepover": True, "day_of_week": 3},   # Sleepover
        
        # Friday
        {"name": "Friday Shift 1", "start_time": "07:30", "end_time": "15:30", "is_sleepover": False, "day_of_week": 4},  # Weekday Day
        {"name": "Friday Shift 2", "start_time": "15:00", "end_time": "20:00", "is_sleepover": False, "day_of_week": 4},  # Weekday Day
        {"name": "Friday Shift 3", "start_time": "15:30", "end_time": "23:30", "is_sleepover": False, "day_of_week": 4},  # Weekday Evening
        {"name": "Friday Shift 4", "start_time": "23:30", "end_time": "07:30", "is_sleepover": True, "day_of_week": 4},   # Sleepover
        
        # Saturday
        {"name": "Saturday Shift 1", "start_time": "07:30", "end_time": "15:30", "is_sleepover": False, "day_of_week": 5},  # Saturday Rate
        {"name": "Saturday Shift 2", "start_time": "15:00", "end_time": "20:00", "is_sleepover": False, "day_of_week": 5},  # Saturday Rate
        {"name": "Saturday Shift 3", "start_time": "15:30", "end_time": "23:30", "is_sleepover": False, "day_of_week": 5},  # Saturday Rate
        {"name": "Saturday Shift 4", "start_time": "23:30", "end_time": "07:30", "is_sleepover": True, "day_of_week": 5},   # Sleepover
        
        # Sunday
        {"name": "Sunday Shift 1", "start_time": "07:30", "end_time": "15:30", "is_sleepover": False, "day_of_week": 6},  # Sunday Rate
        {"name": "Sunday Shift 2", "start_time": "15:00", "end_time": "20:00", "is_sleepover": False, "day_of_week": 6},  # Sunday Rate
        {"name": "Sunday Shift 3", "start_time": "15:30", "end_time": "23:30", "is_sleepover": False, "day_of_week": 6},  # Sunday Rate
        {"name": "Sunday Shift 4", "start_time": "23:30", "end_time": "07:30", "is_sleepover": True, "day_of_week": 6},   # Sleepover
    ]
    
    for template_data in shift_templates:
        template = ShiftTemplate(
            id=str(uuid.uuid4()),
            **template_data
        )
        db.shift_templates.insert_one(template.dict())
    
    # Initialize default settings
    existing_settings = db.settings.find_one()
    if not existing_settings:
        settings = Settings()
        db.settings.insert_one(settings.dict())

# API Endpoints

@app.on_event("startup")
async def startup_event():
    initialize_default_data()

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# Staff endpoints
@app.get("/api/staff")
async def get_staff():
    staff_list = list(db.staff.find({"active": True}, {"_id": 0}))
    return staff_list

@app.post("/api/staff")
async def create_staff(staff: Staff):
    staff.id = str(uuid.uuid4())
    staff.created_at = datetime.now()
    db.staff.insert_one(staff.dict())
    return staff

@app.put("/api/staff/{staff_id}")
async def update_staff(staff_id: str, staff: Staff):
    result = db.staff.update_one({"id": staff_id}, {"$set": staff.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff

@app.delete("/api/staff/{staff_id}")
async def delete_staff(staff_id: str):
    result = db.staff.update_one({"id": staff_id}, {"$set": {"active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"message": "Staff deactivated"}

# Shift template endpoints
@app.get("/api/shift-templates")
async def get_shift_templates():
    templates = list(db.shift_templates.find({}, {"_id": 0}))
    return templates

@app.post("/api/shift-templates")
async def create_shift_template(template: ShiftTemplate):
    template.id = str(uuid.uuid4())
    db.shift_templates.insert_one(template.dict())
    return template

@app.put("/api/shift-templates/{template_id}")
async def update_shift_template(template_id: str, template: ShiftTemplate):
    result = db.shift_templates.update_one({"id": template_id}, {"$set": template.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shift template not found")
    return template

# Roster endpoints
@app.get("/api/roster")
async def get_roster(month: str):
    """Get roster for a specific month (YYYY-MM format)"""
    roster_entries = list(db.roster.find({"date": {"$regex": f"^{month}"}}, {"_id": 0}))
    return roster_entries

@app.post("/api/roster")
async def create_roster_entry(entry: RosterEntry):
    # Get current settings for pay calculation
    settings_doc = db.settings.find_one()
    settings = Settings(**settings_doc) if settings_doc else Settings()
    
    entry.id = str(uuid.uuid4())
    entry = calculate_pay(entry, settings)
    
    db.roster.insert_one(entry.dict())
    return entry

@app.put("/api/roster/{entry_id}")
async def update_roster_entry(entry_id: str, entry: RosterEntry):
    # Get current settings for pay calculation
    settings_doc = db.settings.find_one()
    settings = Settings(**settings_doc) if settings_doc else Settings()
    
    entry = calculate_pay(entry, settings)
    
    result = db.roster.update_one({"id": entry_id}, {"$set": entry.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Roster entry not found")
    return entry

@app.delete("/api/roster/{entry_id}")
async def delete_roster_entry(entry_id: str):
    result = db.roster.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Roster entry not found")
    return {"message": "Roster entry deleted"}

# Settings endpoints
@app.get("/api/settings")
async def get_settings():
    settings_doc = db.settings.find_one({}, {"_id": 0})
    return settings_doc if settings_doc else Settings().dict()

@app.put("/api/settings")
async def update_settings(settings: Settings):
    db.settings.update_one({}, {"$set": settings.dict()}, upsert=True)
    return settings

# Generate monthly roster
@app.post("/api/generate-roster/{month}")
async def generate_monthly_roster(month: str):
    """Generate roster entries for a month based on shift templates"""
    year, month_num = map(int, month.split("-"))
    
    # Get shift templates
    templates = list(db.shift_templates.find())
    
    # Generate entries for each day of the month
    from calendar import monthrange
    _, days_in_month = monthrange(year, month_num)
    
    entries_created = 0
    for day in range(1, days_in_month + 1):
        date_obj = datetime(year, month_num, day)
        date_str = date_obj.strftime("%Y-%m-%d")
        day_of_week = date_obj.weekday()  # 0=Monday
        
        # Find templates for this day of week
        day_templates = [t for t in templates if t["day_of_week"] == day_of_week]
        
        for template in day_templates:
            # Check if entry already exists
            existing = db.roster.find_one({
                "date": date_str,
                "shift_template_id": template["id"]
            })
            
            if not existing:
                entry = RosterEntry(
                    id=str(uuid.uuid4()),
                    date=date_str,
                    shift_template_id=template["id"],
                    start_time=template["start_time"],
                    end_time=template["end_time"],
                    is_sleepover=template["is_sleepover"]
                )
                
                # Calculate pay
                settings_doc = db.settings.find_one()
                settings = Settings(**settings_doc) if settings_doc else Settings()
                entry = calculate_pay(entry, settings)
                
                db.roster.insert_one(entry.dict())
                entries_created += 1
    
    return {"message": f"Generated {entries_created} roster entries for {month}"}

# Clear roster for a month
@app.delete("/api/roster/month/{month}")
async def clear_monthly_roster(month: str):
    """Clear all roster entries for a specific month"""
    result = db.roster.delete_many({"date": {"$regex": f"^{month}"}})
    return {"message": f"Deleted {result.deleted_count} roster entries for {month}"}

# Add individual shift to roster
@app.post("/api/roster/add-shift")
async def add_individual_shift(entry: RosterEntry):
    """Add a single shift to the roster"""
    # Get current settings for pay calculation
    settings_doc = db.settings.find_one()
    settings = Settings(**settings_doc) if settings_doc else Settings()
    
    entry.id = str(uuid.uuid4())
    entry = calculate_pay(entry, settings)
    
    db.roster.insert_one(entry.dict())
    return entry

# ====== EXPORT ENDPOINTS ======

@app.get("/api/export/shift-roster/csv")
async def export_shift_roster_csv(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Department filter")
):
    """Export shift roster data as CSV format"""
    try:
        # Parse dates if provided
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        
        # Fetch data
        shift_data = await export_service.get_shift_roster_data(
            start_date=start_date_obj,
            end_date=end_date_obj,
            department=department
        )
        
        # Generate CSV content
        csv_content = export_service.generate_csv_content(shift_data)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shift_roster_{timestamp}.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/export/pay-summary/csv")
async def export_pay_summary_csv(
    pay_period_start: Optional[str] = Query(None, description="Pay period start date (YYYY-MM-DD)"),
    pay_period_end: Optional[str] = Query(None, description="Pay period end date (YYYY-MM-DD)")
):
    """Export pay summary data as CSV format"""
    try:
        # Parse dates if provided
        start_date_obj = datetime.strptime(pay_period_start, "%Y-%m-%d").date() if pay_period_start else None
        end_date_obj = datetime.strptime(pay_period_end, "%Y-%m-%d").date() if pay_period_end else None
        
        # Fetch data
        pay_data = await export_service.get_pay_summary_data(
            pay_period_start=start_date_obj,
            pay_period_end=end_date_obj
        )
        
        # Generate CSV content
        csv_content = export_service.generate_csv_content(pay_data)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pay_summary_{timestamp}.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/export/workforce-data/excel")
async def export_workforce_data_excel():
    """Export comprehensive workforce data as Excel format with multiple sheets"""
    try:
        # Fetch all required data
        shift_data = await export_service.get_shift_roster_data()
        pay_data = await export_service.get_pay_summary_data()
        employee_data = await export_service.get_workforce_data()
        
        # Prepare data sheets
        data_sheets = {
            "Shift Roster": shift_data,
            "Pay Summary": pay_data,
            "Employee Data": employee_data
        }
        
        # Generate Excel content
        excel_content = export_service.generate_excel_content(data_sheets)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"workforce_data_{timestamp}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/export/pay-summary/pdf")
async def export_pay_summary_pdf(
    pay_period_start: Optional[str] = Query(None, description="Pay period start date (YYYY-MM-DD)"),
    pay_period_end: Optional[str] = Query(None, description="Pay period end date (YYYY-MM-DD)")
):
    """Export pay summary as formatted PDF report"""
    try:
        # Parse dates if provided
        start_date_obj = datetime.strptime(pay_period_start, "%Y-%m-%d").date() if pay_period_start else None
        end_date_obj = datetime.strptime(pay_period_end, "%Y-%m-%d").date() if pay_period_end else None
        
        # Fetch data
        pay_data = await export_service.get_pay_summary_data(
            pay_period_start=start_date_obj,
            pay_period_end=end_date_obj
        )
        
        # Generate title
        period_text = ""
        if start_date_obj and end_date_obj:
            period_text = f" - {start_date_obj} to {end_date_obj}"
        title = f"Pay Summary Report{period_text}"
        
        # Generate PDF content
        pdf_content = export_service.generate_pdf_content(title, pay_data)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pay_summary_{timestamp}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")

# ====== HOLIDAY ENDPOINTS ======

@app.get("/api/holidays/check/{date}")
async def check_public_holiday(
    date: str,
    location: str = Query("QLD", description="Location (QLD, Brisbane)")
):
    """Check if a specific date is a Queensland public holiday"""
    try:
        check_date = datetime.strptime(date, "%Y-%m-%d").date()
        is_holiday = holiday_service.is_public_holiday(check_date, location)
        holiday_name = holiday_service.get_holiday_name(check_date) if is_holiday else ""
        
        return {
            "date": date,
            "is_public_holiday": is_holiday,
            "holiday_name": holiday_name,
            "location": location
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Holiday check failed: {str(e)}")

@app.get("/api/holidays/range")
async def get_holidays_in_range(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    location: str = Query("QLD", description="Location (QLD, Brisbane)")
):
    """Get all public holidays in a date range"""
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        holidays = holiday_service.get_holidays_in_range(start_date_obj, end_date_obj, location)
        
        return {
            "holidays": holidays,
            "start_date": start_date,
            "end_date": end_date,
            "location": location,
            "count": len(holidays)
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Holiday range check failed: {str(e)}")

# ====== END EXPORT/HOLIDAY ENDPOINTS ======

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
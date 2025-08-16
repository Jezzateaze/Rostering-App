import requests
import sys
import json
from datetime import datetime, timedelta, date
import io

class ShiftRosterAPITester:
    def __init__(self, base_url="https://roster-master-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.staff_data = []
        self.shift_templates = []
        self.roster_entries = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, expect_json=True):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                if expect_json:
                    try:
                        response_data = response.json()
                        if isinstance(response_data, list) and len(response_data) > 0:
                            print(f"   Response: {len(response_data)} items returned")
                        elif isinstance(response_data, dict):
                            print(f"   Response keys: {list(response_data.keys())}")
                        return success, response_data
                    except:
                        print(f"   Response: {response.text[:100]}...")
                        return success, {}
                else:
                    # For non-JSON responses (CSV, PDF, Excel)
                    content_type = response.headers.get('content-type', '')
                    content_length = len(response.content)
                    print(f"   Content-Type: {content_type}")
                    print(f"   Content-Length: {content_length} bytes")
                    if content_length > 0:
                        print(f"   ✅ Non-empty response received")
                    else:
                        print(f"   ⚠️  Empty response")
                    return success, response.content
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if expect_json and response.status_code < 400 else response.content

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {} if expect_json else b''

    def test_health_check(self):
        """Test health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        return success

    def test_get_staff(self):
        """Test getting all staff members"""
        success, response = self.run_test(
            "Get All Staff",
            "GET",
            "api/staff",
            200
        )
        if success:
            self.staff_data = response
            print(f"   Found {len(response)} staff members")
            expected_staff = ["Angela", "Chanelle", "Rose", "Caroline", "Nox", "Elina",
                            "Kayla", "Rhet", "Nikita", "Molly", "Felicity", "Issey"]
            actual_names = [staff['name'] for staff in response]
            missing_staff = [name for name in expected_staff if name not in actual_names]
            if missing_staff:
                print(f"   ⚠️  Missing expected staff: {missing_staff}")
            else:
                print(f"   ✅ All 12 expected staff members found")
        return success

    def test_create_staff(self):
        """Test creating a new staff member"""
        test_staff = {
            "name": "Test Staff Member",
            "active": True
        }
        success, response = self.run_test(
            "Create Staff Member",
            "POST",
            "api/staff",
            200,
            data=test_staff
        )
        if success and 'id' in response:
            print(f"   Created staff with ID: {response['id']}")
            return response['id']
        return None

    def test_get_shift_templates(self):
        """Test getting shift templates"""
        success, response = self.run_test(
            "Get Shift Templates",
            "GET",
            "api/shift-templates",
            200
        )
        if success:
            self.shift_templates = response
            print(f"   Found {len(response)} shift templates")
            # Check for expected pattern: 7 days * 4 shifts = 28 templates
            if len(response) == 28:
                print(f"   ✅ Expected 28 shift templates found")
            else:
                print(f"   ⚠️  Expected 28 shift templates, found {len(response)}")
            
            # Check day distribution
            day_counts = {}
            for template in response:
                day = template['day_of_week']
                day_counts[day] = day_counts.get(day, 0) + 1
            
            print(f"   Shifts per day: {day_counts}")
        return success

    def test_get_settings(self):
        """Test getting settings"""
        success, response = self.run_test(
            "Get Settings",
            "GET",
            "api/settings",
            200
        )
        if success:
            print(f"   Pay mode: {response.get('pay_mode', 'N/A')}")
            rates = response.get('rates', {})
            print(f"   Weekday day rate: ${rates.get('weekday_day', 0)}")
            print(f"   Saturday rate: ${rates.get('saturday', 0)}")
            print(f"   Sunday rate: ${rates.get('sunday', 0)}")
            print(f"   Sleepover allowance: ${rates.get('sleepover_default', 0)}")
        return success

    def test_generate_roster(self):
        """Test generating roster for current month"""
        current_month = datetime.now().strftime("%Y-%m")
        success, response = self.run_test(
            f"Generate Roster for {current_month}",
            "POST",
            f"api/generate-roster/{current_month}",
            200
        )
        if success:
            print(f"   {response.get('message', 'Roster generated')}")
        return success

    def test_get_roster(self):
        """Test getting roster for current month"""
        current_month = datetime.now().strftime("%Y-%m")
        success, response = self.run_test(
            f"Get Roster for {current_month}",
            "GET",
            "api/roster",
            200,
            params={"month": current_month}
        )
        if success:
            self.roster_entries = response
            print(f"   Found {len(response)} roster entries")
            if len(response) > 0:
                # Analyze first entry for pay calculation
                entry = response[0]
                print(f"   Sample entry: {entry['date']} {entry['start_time']}-{entry['end_time']}")
                print(f"   Hours: {entry.get('hours_worked', 0)}, Pay: ${entry.get('total_pay', 0)}")
        return success

    def test_shift_type_classification_fix(self):
        """Test the specific shift type classification fix for SCHADS Award compliance"""
        print(f"\n🎯 TESTING SHIFT TYPE CLASSIFICATION FIX")
        print("=" * 60)
        print("🎯 CRITICAL: Testing 15:30-23:30 shift classification as EVENING (not DAY)")
        print("📋 SCHADS Award Rule: Any shift extending past 20:00 should be EVENING for entire duration")
        
        # Test cases specifically for the shift type classification fix
        test_cases = [
            {
                "name": "09:00-17:00 (should be DAY - ends before 20:00)",
                "date": "2025-01-06",  # Monday
                "start_time": "09:00",
                "end_time": "17:00",
                "expected_hours": 8.0,
                "expected_rate": 42.00,  # Day rate
                "expected_pay": 336.00,  # 8 * 42.00
                "expected_shift_type": "DAY"
            },
            {
                "name": "15:00-20:00 (should be DAY - ends exactly at 20:00)",
                "date": "2025-01-06",  # Monday
                "start_time": "15:00",
                "end_time": "20:00",
                "expected_hours": 5.0,
                "expected_rate": 42.00,  # Day rate (ends exactly at 20:00)
                "expected_pay": 210.00,  # 5 * 42.00
                "expected_shift_type": "DAY"
            },
            {
                "name": "15:00-20:01 (should be EVENING - extends past 20:00)",
                "date": "2025-01-06",  # Monday
                "start_time": "15:00",
                "end_time": "20:01",
                "expected_hours": 5.02,  # 5 hours 1 minute
                "expected_rate": 44.50,  # Evening rate
                "expected_pay": 223.39,  # 5.02 * 44.50 (approximately)
                "expected_shift_type": "EVENING"
            },
            {
                "name": "15:30-23:30 (should be EVENING - extends past 20:00) - CRITICAL TEST",
                "date": "2025-01-06",  # Monday
                "start_time": "15:30",
                "end_time": "23:30",
                "expected_hours": 8.0,
                "expected_rate": 44.50,  # Evening rate
                "expected_pay": 356.00,  # 8 * 44.50
                "expected_shift_type": "EVENING"
            },
            {
                "name": "20:00-06:00 (should be NIGHT - overnight shift)",
                "date": "2025-01-06",  # Monday
                "start_time": "20:00",
                "end_time": "06:00",
                "expected_hours": 10.0,
                "expected_rate": 48.50,  # Night rate (overnight shift)
                "expected_pay": 485.00,  # 10 * 48.50
                "expected_shift_type": "NIGHT"
            }
        ]
        
        classification_tests_passed = 0
        critical_test_passed = False
        
        for i, test_case in enumerate(test_cases):
            is_critical = "CRITICAL TEST" in test_case["name"]
            print(f"\n   {'🎯 CRITICAL: ' if is_critical else ''}Testing: {test_case['name']}")
            
            # Create roster entry
            roster_entry = {
                "id": "",  # Will be auto-generated
                "date": test_case["date"],
                "shift_template_id": "test-classification-template",
                "start_time": test_case["start_time"],
                "end_time": test_case["end_time"],
                "is_sleepover": False,
                "is_public_holiday": False,
                "staff_id": None,
                "staff_name": "Test Staff",
                "hours_worked": 0.0,
                "base_pay": 0.0,
                "sleepover_allowance": 0.0,
                "total_pay": 0.0
            }
            
            success, response = self.run_test(
                f"Create {test_case['name']}",
                "POST",
                "api/roster",
                200,
                data=roster_entry
            )
            
            if success:
                hours_worked = response.get('hours_worked', 0)
                total_pay = response.get('total_pay', 0)
                base_pay = response.get('base_pay', 0)
                
                # Calculate expected hourly rate from actual pay
                actual_hourly_rate = base_pay / hours_worked if hours_worked > 0 else 0
                
                print(f"      Time: {test_case['start_time']} - {test_case['end_time']}")
                print(f"      Hours worked: {hours_worked:.2f} (expected: {test_case['expected_hours']:.2f})")
                print(f"      Actual hourly rate: ${actual_hourly_rate:.2f}")
                print(f"      Expected hourly rate: ${test_case['expected_rate']:.2f}")
                print(f"      Total pay: ${total_pay:.2f} (expected: ${test_case['expected_pay']:.2f})")
                
                # Determine actual shift type based on hourly rate
                if abs(actual_hourly_rate - 42.00) < 0.01:
                    actual_shift_type = "DAY"
                elif abs(actual_hourly_rate - 44.50) < 0.01:
                    actual_shift_type = "EVENING"
                elif abs(actual_hourly_rate - 48.50) < 0.01:
                    actual_shift_type = "NIGHT"
                else:
                    actual_shift_type = "UNKNOWN"
                
                print(f"      Actual shift type: {actual_shift_type}")
                print(f"      Expected shift type: {test_case['expected_shift_type']}")
                
                # Check if classification is correct
                hours_correct = abs(hours_worked - test_case['expected_hours']) < 0.1
                rate_correct = abs(actual_hourly_rate - test_case['expected_rate']) < 0.01
                shift_type_correct = actual_shift_type == test_case['expected_shift_type']
                
                if hours_correct and rate_correct and shift_type_correct:
                    print(f"      ✅ Shift type classification CORRECT")
                    classification_tests_passed += 1
                    if is_critical:
                        critical_test_passed = True
                else:
                    print(f"      ❌ Shift type classification INCORRECT")
                    if not hours_correct:
                        print(f"         Hours mismatch: got {hours_worked:.2f}, expected {test_case['expected_hours']:.2f}")
                    if not rate_correct:
                        print(f"         Rate mismatch: got ${actual_hourly_rate:.2f}, expected ${test_case['expected_rate']:.2f}")
                    if not shift_type_correct:
                        print(f"         Shift type mismatch: got {actual_shift_type}, expected {test_case['expected_shift_type']}")
                    
                    if is_critical:
                        print(f"      🚨 CRITICAL TEST FAILED!")
                        print(f"         The 15:30-23:30 shift is NOT being classified as EVENING!")
                        print(f"         This violates SCHADS Award requirements!")
            else:
                print(f"      ❌ Failed to create roster entry for testing")
                if is_critical:
                    print(f"      🚨 CRITICAL TEST COULD NOT BE EXECUTED!")
        
        print(f"\n" + "=" * 60)
        print(f"📊 SHIFT TYPE CLASSIFICATION RESULTS: {classification_tests_passed}/{len(test_cases)} tests passed")
        
        if critical_test_passed:
            print(f"✅ CRITICAL TEST PASSED: 15:30-23:30 shift correctly classified as EVENING")
        else:
            print(f"❌ CRITICAL TEST FAILED: 15:30-23:30 shift NOT correctly classified as EVENING")
        
        if classification_tests_passed == len(test_cases):
            print(f"🎉 ALL SHIFT TYPE CLASSIFICATION TESTS PASSED!")
            print(f"   - Shifts ending at or before 20:00 are DAY shifts")
            print(f"   - Shifts extending past 20:00 are EVENING shifts")
            print(f"   - SCHADS Award compliance verified")
        else:
            print(f"⚠️  SHIFT TYPE CLASSIFICATION ISSUES DETECTED!")
            print(f"   - Check SCHADS Award compliance logic")
            print(f"   - Verify 20:00 cutoff time implementation")
        
        return classification_tests_passed == len(test_cases)

    def test_pay_calculations(self):
        """Test pay calculation accuracy - FOCUS ON SCHADS EVENING SHIFT RULES"""
        print(f"\n💰 Testing SCHADS Award Pay Calculations...")
        print("🎯 CRITICAL TEST: Evening shift rule - 'Starts after 8:00pm OR extends past 8:00pm'")
        
        # Test data for SCHADS evening shift scenarios
        test_cases = [
            {
                "name": "15:30-23:30 shift (extends past 8pm) - CRITICAL TEST",
                "date": "2025-01-06",  # Monday
                "start_time": "15:30",
                "end_time": "23:30",
                "expected_hours": 8.0,
                "expected_rate": 44.50,  # Evening rate
                "expected_pay": 356.00,  # 8 * 44.50
                "shift_type": "EVENING"
            },
            {
                "name": "15:00-20:00 shift (ends exactly at 8pm) - CONTROL TEST",
                "date": "2025-01-06",  # Monday
                "start_time": "15:00",
                "end_time": "20:00",
                "expected_hours": 5.0,
                "expected_rate": 42.00,  # Day rate (ends exactly at 20:00)
                "expected_pay": 210.00,  # 5 * 42.00
                "shift_type": "DAY"
            },
            {
                "name": "20:30-23:30 shift (starts after 8pm) - CRITICAL TEST",
                "date": "2025-01-06",  # Monday
                "start_time": "20:30",
                "end_time": "23:30",
                "expected_hours": 3.0,
                "expected_rate": 44.50,  # Evening rate
                "expected_pay": 133.50,  # 3 * 44.50
                "shift_type": "EVENING"
            },
            {
                "name": "07:30-15:30 shift (ends before 8pm) - CONTROL TEST",
                "date": "2025-01-06",  # Monday
                "start_time": "07:30",
                "end_time": "15:30",
                "expected_hours": 8.0,
                "expected_rate": 42.00,  # Day rate
                "expected_pay": 336.00,  # 8 * 42.00
                "shift_type": "DAY"
            },
            {
                "name": "Weekday Night Shift (23:30-07:30)",
                "date": "2025-01-06",  # Monday
                "start_time": "23:30",
                "end_time": "07:30",
                "expected_hours": 8.0,
                "expected_rate": 48.50,
                "expected_pay": 388.00,
                "is_sleepover": True,
                "expected_sleepover": 175.00,
                "shift_type": "NIGHT"
            },
            {
                "name": "Saturday Shift (07:30-15:30)",
                "date": "2025-01-11",  # Saturday
                "start_time": "07:30",
                "end_time": "15:30",
                "expected_hours": 8.0,
                "expected_rate": 57.50,
                "expected_pay": 460.00,
                "shift_type": "SATURDAY"
            },
            {
                "name": "Sunday Shift (07:30-15:30)",
                "date": "2025-01-12",  # Sunday
                "start_time": "07:30",
                "end_time": "15:30",
                "expected_hours": 8.0,
                "expected_rate": 74.00,
                "expected_pay": 592.00,
                "shift_type": "SUNDAY"
            }
        ]

        pay_tests_passed = 0
        critical_evening_tests_passed = 0
        critical_evening_tests_total = 3  # First 3 are the critical evening shift tests
        
        for i, test_case in enumerate(test_cases):
            is_critical = i < critical_evening_tests_total
            print(f"\n   {'🎯 CRITICAL: ' if is_critical else ''}Testing: {test_case['name']}")
            
            # Create roster entry (id will be auto-generated by backend)
            roster_entry = {
                "id": "",  # Will be auto-generated
                "date": test_case["date"],
                "shift_template_id": "test-template",
                "start_time": test_case["start_time"],
                "end_time": test_case["end_time"],
                "is_sleepover": test_case.get("is_sleepover", False),
                "is_public_holiday": False,
                "staff_id": None,
                "staff_name": None,
                "hours_worked": 0.0,
                "base_pay": 0.0,
                "sleepover_allowance": 0.0,
                "total_pay": 0.0
            }
            
            success, response = self.run_test(
                f"Create {test_case['name']}",
                "POST",
                "api/roster",
                200,
                data=roster_entry
            )
            
            if success:
                hours_worked = response.get('hours_worked', 0)
                total_pay = response.get('total_pay', 0)
                base_pay = response.get('base_pay', 0)
                sleepover_allowance = response.get('sleepover_allowance', 0)
                
                print(f"      Expected shift type: {test_case.get('shift_type', 'N/A')}")
                print(f"      Hours worked: {hours_worked} (expected: {test_case['expected_hours']})")
                print(f"      Base pay: ${base_pay}")
                print(f"      Sleepover allowance: ${sleepover_allowance}")
                print(f"      Total pay: ${total_pay} (expected: ${test_case['expected_pay']})")
                
                # Check calculations
                hours_correct = abs(hours_worked - test_case['expected_hours']) < 0.1
                
                if test_case.get('is_sleepover'):
                    # For sleepover shifts, total pay = sleepover allowance (in default mode)
                    pay_correct = abs(total_pay - test_case['expected_sleepover']) < 0.01
                else:
                    pay_correct = abs(total_pay - test_case['expected_pay']) < 0.01
                
                if hours_correct and pay_correct:
                    print(f"      ✅ Pay calculation correct")
                    pay_tests_passed += 1
                    if is_critical:
                        critical_evening_tests_passed += 1
                else:
                    print(f"      ❌ Pay calculation incorrect")
                    if not hours_correct:
                        print(f"         Hours mismatch: got {hours_worked}, expected {test_case['expected_hours']}")
                    if not pay_correct:
                        expected = test_case['expected_sleepover'] if test_case.get('is_sleepover') else test_case['expected_pay']
                        print(f"         Pay mismatch: got ${total_pay}, expected ${expected}")
                    
                    if is_critical:
                        print(f"      🚨 CRITICAL EVENING SHIFT TEST FAILED!")
                        print(f"         This indicates the SCHADS evening shift rule may not be working correctly")
            else:
                if is_critical:
                    print(f"      🚨 CRITICAL TEST FAILED - Could not create roster entry")

        print(f"\n   🎯 CRITICAL Evening Shift Tests: {critical_evening_tests_passed}/{critical_evening_tests_total} passed")
        print(f"   📊 Total Pay calculation tests: {pay_tests_passed}/{len(test_cases)} passed")
        
        if critical_evening_tests_passed < critical_evening_tests_total:
            print(f"   ❌ CRITICAL ISSUE: Evening shift calculation logic needs attention!")
            print(f"      Expected: Shifts extending past 8:00pm should use evening rate ($44.50/hr)")
        else:
            print(f"   ✅ All critical evening shift tests passed!")
        
        return pay_tests_passed == len(test_cases)

    def analyze_existing_pay_calculations(self):
        """Analyze existing roster entries to verify pay calculations"""
        if not self.roster_entries:
            print("⚠️  No roster entries available for analysis")
            return False
        
        print(f"\n💰 Analyzing Existing Pay Calculations...")
        print(f"   Analyzing {len(self.roster_entries)} roster entries...")
        
        # Group by shift type
        shift_analysis = {
            'weekday_day': [],
            'weekday_evening': [],
            'weekday_night': [],
            'saturday': [],
            'sunday': [],
            'sleepover': []
        }
        
        for entry in self.roster_entries[:10]:  # Analyze first 10 entries
            date_obj = datetime.strptime(entry['date'], "%Y-%m-%d")
            day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
            start_hour = int(entry['start_time'].split(':')[0])
            
            if entry.get('is_sleepover'):
                shift_analysis['sleepover'].append(entry)
            elif day_of_week == 5:  # Saturday
                shift_analysis['saturday'].append(entry)
            elif day_of_week == 6:  # Sunday
                shift_analysis['sunday'].append(entry)
            elif start_hour >= 22 or start_hour < 6:
                shift_analysis['weekday_night'].append(entry)
            elif start_hour >= 20:
                shift_analysis['weekday_evening'].append(entry)
            else:
                shift_analysis['weekday_day'].append(entry)
        
        # Expected rates
        expected_rates = {
            'weekday_day': 42.00,
            'weekday_evening': 44.50,
            'weekday_night': 48.50,
            'saturday': 57.50,
            'sunday': 74.00,
            'sleepover': 175.00  # Default sleepover allowance
        }
        
        analysis_passed = True
        
        for shift_type, entries in shift_analysis.items():
            if not entries:
                continue
                
            print(f"\n   {shift_type.replace('_', ' ').title()} Shifts:")
            for entry in entries[:3]:  # Check first 3 of each type
                hours = entry.get('hours_worked', 0)
                total_pay = entry.get('total_pay', 0)
                base_pay = entry.get('base_pay', 0)
                sleepover_allowance = entry.get('sleepover_allowance', 0)
                
                if shift_type == 'sleepover':
                    expected_pay = expected_rates[shift_type]
                    actual_pay = sleepover_allowance
                else:
                    expected_pay = hours * expected_rates[shift_type]
                    actual_pay = base_pay
                
                pay_correct = abs(actual_pay - expected_pay) < 0.01
                
                print(f"      {entry['date']} {entry['start_time']}-{entry['end_time']}: "
                      f"{hours}h, ${actual_pay:.2f} (expected: ${expected_pay:.2f}) "
                      f"{'✅' if pay_correct else '❌'}")
                
                if not pay_correct:
                    analysis_passed = False
        
        return analysis_passed

    def test_roster_assignment(self):
        """Test assigning staff to roster entries"""
        if not self.roster_entries or not self.staff_data:
            print("⚠️  No roster entries or staff data available for assignment test")
            return False
        
        # Get first roster entry and first staff member
        entry = self.roster_entries[0]
        staff_member = self.staff_data[0]
        
        # Update roster entry with staff assignment
        updated_entry = {
            **entry,
            "staff_id": staff_member['id'],
            "staff_name": staff_member['name']
        }
        
        success, response = self.run_test(
            "Assign Staff to Roster Entry",
            "PUT",
            f"api/roster/{entry['id']}",
            200,
            data=updated_entry
        )
        
        if success:
            print(f"   Assigned {staff_member['name']} to shift on {entry['date']}")
        
        return success

    def test_delete_individual_shift(self):
        """Test deleting individual roster entries - CRITICAL DELETE FUNCTIONALITY"""
        print(f"\n🗑️  Testing Individual Shift Deletion...")
        
        # First, ensure we have some roster entries to delete
        if not self.roster_entries:
            print("   No roster entries available, generating test data...")
            current_month = datetime.now().strftime("%Y-%m")
            self.test_generate_roster()
            self.test_get_roster()
        
        if not self.roster_entries:
            print("   ❌ No roster entries available for deletion test")
            return False
        
        # Test 1: Delete with valid ID
        entry_to_delete = self.roster_entries[0]
        entry_id = entry_to_delete['id']
        
        print(f"   🎯 Testing deletion of entry: {entry_to_delete['date']} {entry_to_delete['start_time']}-{entry_to_delete['end_time']}")
        
        success, response = self.run_test(
            "Delete Individual Shift (Valid ID)",
            "DELETE",
            f"api/roster/{entry_id}",
            200
        )
        
        if success:
            print(f"   ✅ Successfully deleted roster entry")
            print(f"   Response: {response.get('message', 'No message')}")
            
            # Verify the entry is actually deleted by trying to get it
            verify_success, verify_response = self.run_test(
                "Verify Deletion (Should get 404)",
                "DELETE",
                f"api/roster/{entry_id}",
                404
            )
            
            if verify_success:
                print(f"   ✅ Deletion verified - entry no longer exists")
            else:
                print(f"   ❌ Deletion verification failed - entry may still exist")
                success = False
        
        # Test 2: Delete with invalid ID (should return 404)
        invalid_id = "non-existent-id-12345"
        
        invalid_success, invalid_response = self.run_test(
            "Delete Individual Shift (Invalid ID)",
            "DELETE",
            f"api/roster/{invalid_id}",
            404
        )
        
        if invalid_success:
            print(f"   ✅ Correctly returned 404 for invalid ID")
        else:
            print(f"   ❌ Should have returned 404 for invalid ID")
        
        return success and invalid_success

    def test_clear_monthly_roster(self):
        """Test clearing entire monthly roster - CRITICAL DELETE FUNCTIONALITY"""
        print(f"\n🗑️  Testing Monthly Roster Clearing...")
        
        # Use current month for testing
        current_month = datetime.now().strftime("%Y-%m")
        
        # First, ensure we have roster data for the month
        print(f"   Ensuring roster data exists for {current_month}...")
        self.test_generate_roster()
        
        # Get roster count before deletion
        before_success, before_response = self.run_test(
            f"Get Roster Count Before Deletion",
            "GET",
            "api/roster",
            200,
            params={"month": current_month}
        )
        
        entries_before = len(before_response) if before_success else 0
        print(f"   Roster entries before deletion: {entries_before}")
        
        if entries_before == 0:
            print("   ⚠️  No roster entries found to delete")
            return False
        
        # Test clearing the monthly roster
        success, response = self.run_test(
            f"Clear Monthly Roster for {current_month}",
            "DELETE",
            f"api/roster/month/{current_month}",
            200
        )
        
        if success:
            message = response.get('message', '')
            print(f"   ✅ Clear roster response: {message}")
            
            # Extract deleted count from message
            import re
            match = re.search(r'Deleted (\d+) roster entries', message)
            deleted_count = int(match.group(1)) if match else 0
            
            print(f"   Deleted {deleted_count} entries")
            
            # Verify the roster is actually cleared
            after_success, after_response = self.run_test(
                f"Verify Roster Cleared",
                "GET",
                "api/roster",
                200,
                params={"month": current_month}
            )
            
            if after_success:
                entries_after = len(after_response)
                print(f"   Roster entries after deletion: {entries_after}")
                
                if entries_after == 0:
                    print(f"   ✅ Monthly roster successfully cleared")
                    return True
                else:
                    print(f"   ❌ Roster not fully cleared - {entries_after} entries remain")
                    return False
            else:
                print(f"   ❌ Could not verify roster clearing")
                return False
        else:
            print(f"   ❌ Failed to clear monthly roster")
            return False

    def test_delete_functionality_comprehensive(self):
        """Comprehensive test of all delete functionality"""
        print(f"\n🎯 COMPREHENSIVE DELETE FUNCTIONALITY TEST")
        print("=" * 50)
        
        # Test month for comprehensive testing
        test_month = datetime.now().strftime("%Y-%m")
        
        # Step 1: Generate fresh test data
        print(f"Step 1: Generating test data for {test_month}...")
        gen_success = self.test_generate_roster()
        if not gen_success:
            print("❌ Failed to generate test data")
            return False
        
        # Step 2: Get initial roster count
        get_success, initial_roster = self.run_test(
            "Get Initial Roster Count",
            "GET",
            "api/roster",
            200,
            params={"month": test_month}
        )
        
        if not get_success:
            print("❌ Failed to get initial roster")
            return False
        
        initial_count = len(initial_roster)
        print(f"   Initial roster entries: {initial_count}")
        
        if initial_count == 0:
            print("❌ No roster entries to test deletion")
            return False
        
        # Step 3: Test individual deletion
        print(f"\nStep 2: Testing individual shift deletion...")
        entry_to_delete = initial_roster[0]
        
        delete_success, delete_response = self.run_test(
            "Delete Single Entry",
            "DELETE",
            f"api/roster/{entry_to_delete['id']}",
            200
        )
        
        if not delete_success:
            print("❌ Individual deletion failed")
            return False
        
        # Step 4: Verify individual deletion
        get_success, after_individual = self.run_test(
            "Get Roster After Individual Delete",
            "GET",
            "api/roster",
            200,
            params={"month": test_month}
        )
        
        if get_success:
            after_individual_count = len(after_individual)
            expected_count = initial_count - 1
            
            if after_individual_count == expected_count:
                print(f"   ✅ Individual deletion verified: {after_individual_count} entries (was {initial_count})")
            else:
                print(f"   ❌ Individual deletion failed: expected {expected_count}, got {after_individual_count}")
                return False
        
        # Step 5: Test monthly clearing
        print(f"\nStep 3: Testing monthly roster clearing...")
        clear_success, clear_response = self.run_test(
            "Clear Monthly Roster",
            "DELETE",
            f"api/roster/month/{test_month}",
            200
        )
        
        if not clear_success:
            print("❌ Monthly clearing failed")
            return False
        
        # Step 6: Verify monthly clearing
        get_success, final_roster = self.run_test(
            "Get Roster After Monthly Clear",
            "GET",
            "api/roster",
            200,
            params={"month": test_month}
        )
        
        if get_success:
            final_count = len(final_roster)
            
            if final_count == 0:
                print(f"   ✅ Monthly clearing verified: {final_count} entries remaining")
                print(f"\n🎉 ALL DELETE FUNCTIONALITY TESTS PASSED!")
                return True
            else:
                print(f"   ❌ Monthly clearing failed: {final_count} entries still exist")
                return False
        
        return False

    def test_export_csv_shift_roster(self):
        """Test CSV export for shift roster data"""
        print(f"\n📊 Testing CSV Export - Shift Roster...")
        
        # Test without filters
        success, response = self.run_test(
            "Export Shift Roster CSV (No Filters)",
            "GET",
            "api/export/shift-roster/csv",
            200,
            expect_json=False
        )
        
        if success and len(response) > 0:
            print(f"   ✅ CSV export successful without filters")
        
        # Test with date filters
        start_date = "2025-01-01"
        end_date = "2025-01-31"
        
        success_filtered, response_filtered = self.run_test(
            "Export Shift Roster CSV (With Date Filters)",
            "GET",
            "api/export/shift-roster/csv",
            200,
            params={"start_date": start_date, "end_date": end_date},
            expect_json=False
        )
        
        if success_filtered and len(response_filtered) > 0:
            print(f"   ✅ CSV export successful with date filters")
        
        return success and success_filtered

    def test_export_csv_pay_summary(self):
        """Test CSV export for pay summary data"""
        print(f"\n💰 Testing CSV Export - Pay Summary...")
        
        # Test without filters
        success, response = self.run_test(
            "Export Pay Summary CSV (No Filters)",
            "GET",
            "api/export/pay-summary/csv",
            200,
            expect_json=False
        )
        
        if success and len(response) > 0:
            print(f"   ✅ Pay summary CSV export successful without filters")
        
        # Test with pay period filters
        pay_start = "2025-01-01"
        pay_end = "2025-01-31"
        
        success_filtered, response_filtered = self.run_test(
            "Export Pay Summary CSV (With Pay Period)",
            "GET",
            "api/export/pay-summary/csv",
            200,
            params={"pay_period_start": pay_start, "pay_period_end": pay_end},
            expect_json=False
        )
        
        if success_filtered and len(response_filtered) > 0:
            print(f"   ✅ Pay summary CSV export successful with pay period filters")
        
        return success and success_filtered

    def test_export_excel_workforce(self):
        """Test Excel export for comprehensive workforce data"""
        print(f"\n📈 Testing Excel Export - Workforce Data...")
        
        success, response = self.run_test(
            "Export Workforce Data Excel (Multi-sheet)",
            "GET",
            "api/export/workforce-data/excel",
            200,
            expect_json=False
        )
        
        if success and len(response) > 0:
            print(f"   ✅ Excel export successful - comprehensive multi-sheet export")
        
        return success

    def test_export_pdf_pay_summary(self):
        """Test PDF export for pay summary"""
        print(f"\n📄 Testing PDF Export - Pay Summary...")
        
        # Test without filters
        success, response = self.run_test(
            "Export Pay Summary PDF (No Filters)",
            "GET",
            "api/export/pay-summary/pdf",
            200,
            expect_json=False
        )
        
        if success and len(response) > 0:
            print(f"   ✅ PDF export successful without filters")
        
        # Test with period filters
        pay_start = "2025-01-01"
        pay_end = "2025-01-31"
        
        success_filtered, response_filtered = self.run_test(
            "Export Pay Summary PDF (With Period)",
            "GET",
            "api/export/pay-summary/pdf",
            200,
            params={"pay_period_start": pay_start, "pay_period_end": pay_end},
            expect_json=False
        )
        
        if success_filtered and len(response_filtered) > 0:
            print(f"   ✅ PDF export successful with period filters")
        
        return success and success_filtered

    def test_queensland_holiday_detection(self):
        """Test Queensland public holiday detection endpoints"""
        print(f"\n🎄 Testing Queensland Public Holiday Detection...")
        
        # Test specific known holidays
        test_cases = [
            {
                "date": "2025-01-01",
                "name": "New Year's Day",
                "expected": True,
                "location": "QLD"
            },
            {
                "date": "2025-04-18",
                "name": "Good Friday",
                "expected": True,
                "location": "QLD"
            },
            {
                "date": "2025-08-13",
                "name": "Royal Queensland Show (Brisbane only)",
                "expected": True,
                "location": "Brisbane"
            },
            {
                "date": "2025-08-13",
                "name": "Royal Queensland Show (Non-Brisbane QLD)",
                "expected": False,
                "location": "QLD"
            },
            {
                "date": "2025-06-15",
                "name": "Regular non-holiday date",
                "expected": False,
                "location": "QLD"
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            print(f"\n   Testing: {test_case['name']} ({test_case['date']})")
            
            params = {"location": test_case["location"]} if test_case["location"] != "QLD" else {}
            
            success, response = self.run_test(
                f"Check Holiday: {test_case['date']}",
                "GET",
                f"api/holidays/check/{test_case['date']}",
                200,
                params=params
            )
            
            if success:
                is_holiday = response.get("is_public_holiday", False)
                holiday_name = response.get("holiday_name", "")
                location = response.get("location", "")
                
                print(f"      Result: {'Holiday' if is_holiday else 'Not Holiday'}")
                print(f"      Holiday name: {holiday_name}")
                print(f"      Location: {location}")
                
                if is_holiday == test_case["expected"]:
                    print(f"      ✅ Correct holiday detection")
                else:
                    print(f"      ❌ Incorrect holiday detection - Expected: {test_case['expected']}, Got: {is_holiday}")
                    all_passed = False
            else:
                print(f"      ❌ Failed to check holiday")
                all_passed = False
        
        return all_passed

    def test_holiday_range_endpoint(self):
        """Test holiday range endpoint"""
        print(f"\n📅 Testing Holiday Range Endpoint...")
        
        success, response = self.run_test(
            "Get Holidays in Range (2025 full year)",
            "GET",
            "api/holidays/range",
            200,
            params={
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "location": "QLD"
            }
        )
        
        if success:
            holidays = response.get("holidays", [])
            count = response.get("count", 0)
            
            print(f"   Found {count} holidays in 2025 for QLD")
            
            # Display first few holidays
            for i, holiday in enumerate(holidays[:5]):
                print(f"      {holiday['date']}: {holiday['name']}")
            
            if count > 5:
                print(f"      ... and {count - 5} more holidays")
            
            # Verify we have reasonable number of holidays (should be 10+ for QLD)
            if count >= 10:
                print(f"   ✅ Reasonable number of holidays found")
                return True
            else:
                print(f"   ❌ Too few holidays found - expected 10+, got {count}")
                return False
        
        return False

    def test_integrated_holiday_roster_creation(self):
        """Test creating roster entries on public holidays and verify $88.50/hr rate"""
        print(f"\n🎯 Testing Integrated Holiday Roster Creation...")
        
        # Create roster entry for New Year's Day 2025 (known QLD public holiday)
        holiday_entry = {
            "id": "",  # Will be auto-generated
            "date": "2025-01-01",  # New Year's Day
            "shift_template_id": "test-holiday-template",
            "start_time": "09:00",
            "end_time": "17:00",
            "is_sleepover": False,
            "is_public_holiday": False,  # Let system auto-detect
            "staff_id": None,
            "staff_name": "Test Staff",
            "hours_worked": 0.0,
            "base_pay": 0.0,
            "sleepover_allowance": 0.0,
            "total_pay": 0.0
        }
        
        success, response = self.run_test(
            "Create Roster Entry on Public Holiday (Auto-detect)",
            "POST",
            "api/roster",
            200,
            data=holiday_entry
        )
        
        if success:
            hours_worked = response.get('hours_worked', 0)
            total_pay = response.get('total_pay', 0)
            base_pay = response.get('base_pay', 0)
            is_public_holiday = response.get('is_public_holiday', False)
            
            print(f"   Holiday auto-detected: {is_public_holiday}")
            print(f"   Hours worked: {hours_worked}")
            print(f"   Base pay: ${base_pay}")
            print(f"   Total pay: ${total_pay}")
            
            # Expected: 8 hours * $88.50/hr = $708.00
            expected_pay = 8.0 * 88.50
            
            if is_public_holiday and abs(total_pay - expected_pay) < 0.01:
                print(f"   ✅ Public holiday correctly detected and $88.50/hr rate applied")
                return True
            else:
                print(f"   ❌ Public holiday rate not correctly applied")
                print(f"      Expected: ${expected_pay:.2f}, Got: ${total_pay:.2f}")
                return False
        
        return False

    def test_export_with_holiday_data(self):
        """Test that export functionality works with holiday-integrated data"""
        print(f"\n📊 Testing Export with Holiday Data...")
        
        # First create some roster entries including holidays
        self.test_integrated_holiday_roster_creation()
        
        # Test CSV export includes holiday data
        success_csv, response_csv = self.run_test(
            "Export CSV with Holiday Data",
            "GET",
            "api/export/shift-roster/csv",
            200,
            params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
            expect_json=False
        )
        
        # Test PDF export includes holiday data
        success_pdf, response_pdf = self.run_test(
            "Export PDF with Holiday Data",
            "GET",
            "api/export/pay-summary/pdf",
            200,
            params={"pay_period_start": "2025-01-01", "pay_period_end": "2025-01-31"},
            expect_json=False
        )
        
        if success_csv and success_pdf and len(response_csv) > 0 and len(response_pdf) > 0:
            print(f"   ✅ Export functionality works with holiday-integrated data")
            return True
        else:
            print(f"   ❌ Export functionality failed with holiday data")
            return False

    def test_roster_template_system(self):
        """Comprehensive test of the roster template system"""
        print(f"\n🎯 COMPREHENSIVE ROSTER TEMPLATE SYSTEM TEST")
        print("=" * 60)
        
        # Store template ID for later tests
        template_id = None
        template_name = "Test Template January 2025"
        template_description = "Test template description for January roster"
        source_month = "2025-01"
        target_month = "2025-02"
        
        # Step 1: Ensure we have roster data for January 2025
        print(f"\nStep 1: Ensuring roster data exists for {source_month}...")
        gen_success, gen_response = self.run_test(
            f"Generate Roster for {source_month}",
            "POST",
            f"api/generate-roster/{source_month}",
            200
        )
        
        if not gen_success:
            print(f"   ❌ Failed to generate roster data for {source_month}")
            return False
        
        print(f"   ✅ Roster data generated for {source_month}")
        
        # Step 2: Save current roster as template
        print(f"\nStep 2: Testing Save Current Roster as Template...")
        save_success, save_response = self.run_test(
            "Save Roster as Template",
            "POST",
            "api/roster-templates",
            200,
            params={
                "name": template_name,
                "description": template_description,
                "month": source_month
            }
        )
        
        if not save_success:
            print(f"   ❌ Failed to save roster as template")
            return False
        
        template_id = save_response.get("template_id")
        shift_count = save_response.get("shift_count", 0)
        
        print(f"   ✅ Template saved successfully")
        print(f"   Template ID: {template_id}")
        print(f"   Shift count: {shift_count}")
        
        if not template_id:
            print(f"   ❌ No template ID returned")
            return False
        
        # Step 3: Get all templates
        print(f"\nStep 3: Testing Get All Templates...")
        get_all_success, get_all_response = self.run_test(
            "Get All Roster Templates",
            "GET",
            "api/roster-templates",
            200
        )
        
        if not get_all_success:
            print(f"   ❌ Failed to get all templates")
            return False
        
        templates_found = len(get_all_response)
        print(f"   ✅ Retrieved {templates_found} templates")
        
        # Verify our template is in the list
        our_template = None
        for template in get_all_response:
            if template.get("id") == template_id:
                our_template = template
                break
        
        if not our_template:
            print(f"   ❌ Our template not found in the list")
            return False
        
        print(f"   ✅ Our template found: '{our_template.get('name')}'")
        
        # Step 4: Get specific template
        print(f"\nStep 4: Testing Get Specific Template...")
        get_specific_success, get_specific_response = self.run_test(
            "Get Specific Template",
            "GET",
            f"api/roster-templates/{template_id}",
            200
        )
        
        if not get_specific_success:
            print(f"   ❌ Failed to get specific template")
            return False
        
        template_shifts = get_specific_response.get("shifts", [])
        print(f"   ✅ Template retrieved with {len(template_shifts)} shifts")
        print(f"   Template name: {get_specific_response.get('name')}")
        print(f"   Template description: {get_specific_response.get('description')}")
        
        # Step 5: Generate roster from template
        print(f"\nStep 5: Testing Generate Roster from Template...")
        generate_success, generate_response = self.run_test(
            "Generate Roster from Template",
            "POST",
            f"api/generate-roster/{target_month}",
            200,
            params={"template_id": template_id}
        )
        
        if not generate_success:
            print(f"   ❌ Failed to generate roster from template")
            return False
        
        entries_generated = generate_response.get("entries_generated", 0)
        print(f"   ✅ Generated {entries_generated} roster entries for {target_month}")
        print(f"   Template used: {generate_response.get('template_name')}")
        
        # Step 6: Verify generated roster
        print(f"\nStep 6: Verifying Generated Roster...")
        verify_success, verify_response = self.run_test(
            f"Get Generated Roster for {target_month}",
            "GET",
            "api/roster",
            200,
            params={"month": target_month}
        )
        
        if not verify_success:
            print(f"   ❌ Failed to get generated roster")
            return False
        
        generated_entries = len(verify_response)
        print(f"   ✅ Found {generated_entries} entries in {target_month}")
        
        # Verify entries have correct structure and no staff assignments
        if generated_entries > 0:
            sample_entry = verify_response[0]
            print(f"   Sample entry date: {sample_entry.get('date')}")
            print(f"   Sample entry times: {sample_entry.get('start_time')} - {sample_entry.get('end_time')}")
            print(f"   Staff assigned: {sample_entry.get('staff_name', 'None')}")
            print(f"   Total pay calculated: ${sample_entry.get('total_pay', 0):.2f}")
            
            # Verify no staff assignments (should be None/null)
            staff_assigned = any(entry.get('staff_id') for entry in verify_response)
            if not staff_assigned:
                print(f"   ✅ No staff assignments copied (correct behavior)")
            else:
                print(f"   ❌ Staff assignments were copied (incorrect behavior)")
        
        # Step 7: Test generate roster without template (default behavior)
        print(f"\nStep 7: Testing Generate Roster without Template...")
        test_month = "2025-03"
        default_success, default_response = self.run_test(
            "Generate Roster without Template (Default)",
            "POST",
            f"api/generate-roster/{test_month}",
            200
        )
        
        if not default_success:
            print(f"   ❌ Failed to generate roster with default templates")
            return False
        
        print(f"   ✅ Default roster generation successful")
        print(f"   Message: {default_response.get('message', 'No message')}")
        
        # Step 8: Delete template
        print(f"\nStep 8: Testing Delete Template...")
        delete_success, delete_response = self.run_test(
            "Delete Roster Template",
            "DELETE",
            f"api/roster-templates/{template_id}",
            200
        )
        
        if not delete_success:
            print(f"   ❌ Failed to delete template")
            return False
        
        print(f"   ✅ Template deleted successfully")
        print(f"   Message: {delete_response.get('message', 'No message')}")
        
        # Step 9: Verify template deletion
        print(f"\nStep 9: Verifying Template Deletion...")
        verify_delete_success, verify_delete_response = self.run_test(
            "Verify Template Deleted (Should get 404)",
            "GET",
            f"api/roster-templates/{template_id}",
            404
        )
        
        if verify_delete_success:
            print(f"   ✅ Template deletion verified - returns 404")
        else:
            print(f"   ❌ Template may still exist")
            return False
        
        # Final summary
        print(f"\n" + "=" * 60)
        print(f"🎉 ROSTER TEMPLATE SYSTEM TEST COMPLETED SUCCESSFULLY!")
        print(f"✅ All 9 test steps passed:")
        print(f"   1. ✅ Generated source roster data")
        print(f"   2. ✅ Saved roster as template")
        print(f"   3. ✅ Retrieved all templates")
        print(f"   4. ✅ Retrieved specific template")
        print(f"   5. ✅ Generated roster from template")
        print(f"   6. ✅ Verified generated roster structure")
        print(f"   7. ✅ Tested default roster generation")
        print(f"   8. ✅ Deleted template")
        print(f"   9. ✅ Verified template deletion")
        print(f"=" * 60)
        
        return True

    def test_roster_template_edge_cases(self):
        """Test edge cases for roster template system"""
        print(f"\n🔍 Testing Roster Template Edge Cases...")
        
        # Test 1: Save template from non-existent month
        print(f"\n   Test 1: Save template from non-existent month...")
        edge_success_1, edge_response_1 = self.run_test(
            "Save Template from Non-existent Month",
            "POST",
            "api/roster-templates",
            404,  # Should return 404
            params={
                "name": "Non-existent Template",
                "description": "Should fail",
                "month": "2025-12"  # Assuming no data for December
            }
        )
        
        if edge_success_1:
            print(f"      ✅ Correctly returned 404 for non-existent month")
        else:
            print(f"      ❌ Should have returned 404 for non-existent month")
        
        # Test 2: Get non-existent template
        print(f"\n   Test 2: Get non-existent template...")
        fake_template_id = "non-existent-template-id"
        edge_success_2, edge_response_2 = self.run_test(
            "Get Non-existent Template",
            "GET",
            f"api/roster-templates/{fake_template_id}",
            404
        )
        
        if edge_success_2:
            print(f"      ✅ Correctly returned 404 for non-existent template")
        else:
            print(f"      ❌ Should have returned 404 for non-existent template")
        
        # Test 3: Delete non-existent template
        print(f"\n   Test 3: Delete non-existent template...")
        edge_success_3, edge_response_3 = self.run_test(
            "Delete Non-existent Template",
            "DELETE",
            f"api/roster-templates/{fake_template_id}",
            404
        )
        
        if edge_success_3:
            print(f"      ✅ Correctly returned 404 for non-existent template deletion")
        else:
            print(f"      ❌ Should have returned 404 for non-existent template deletion")
        
        # Test 4: Generate roster with non-existent template
        print(f"\n   Test 4: Generate roster with non-existent template...")
        edge_success_4, edge_response_4 = self.run_test(
            "Generate Roster with Non-existent Template",
            "POST",
            "api/generate-roster/2025-04",
            404,
            params={"template_id": fake_template_id}
        )
        
        if edge_success_4:
            print(f"      ✅ Correctly returned 404 for non-existent template in generation")
        else:
            print(f"      ❌ Should have returned 404 for non-existent template in generation")
        
        edge_tests_passed = sum([edge_success_1, edge_success_2, edge_success_3, edge_success_4])
        print(f"\n   📊 Edge case tests: {edge_tests_passed}/4 passed")
        
        return edge_tests_passed == 4

    def test_comprehensive_export_and_holiday_system(self):
        """Comprehensive test of export and holiday systems"""
        print(f"\n🎯 COMPREHENSIVE EXPORT & HOLIDAY SYSTEM TEST")
        print("=" * 60)
        
        test_results = []
        
        # Export functionality tests
        print("\n📊 EXPORT FUNCTIONALITY TESTS")
        test_results.append(("CSV Shift Roster Export", self.test_export_csv_shift_roster()))
        test_results.append(("CSV Pay Summary Export", self.test_export_csv_pay_summary()))
        test_results.append(("Excel Workforce Export", self.test_export_excel_workforce()))
        test_results.append(("PDF Pay Summary Export", self.test_export_pdf_pay_summary()))
        
        # Holiday detection tests
        print("\n🎄 HOLIDAY DETECTION TESTS")
        test_results.append(("Queensland Holiday Detection", self.test_queensland_holiday_detection()))
        test_results.append(("Holiday Range Endpoint", self.test_holiday_range_endpoint()))
        
        # Integration tests
        print("\n🔗 INTEGRATION TESTS")
        test_results.append(("Holiday Roster Integration", self.test_integrated_holiday_roster_creation()))
        test_results.append(("Export with Holiday Data", self.test_export_with_holiday_data()))
        
        # Summary
        passed_tests = sum(1 for _, result in test_results if result)
        total_tests = len(test_results)
        
        print(f"\n" + "=" * 60)
        print(f"📊 EXPORT & HOLIDAY SYSTEM RESULTS: {passed_tests}/{total_tests} tests passed")
        print("=" * 60)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status}: {test_name}")
        
        if passed_tests == total_tests:
            print(f"\n🎉 ALL EXPORT & HOLIDAY SYSTEM TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  SOME EXPORT & HOLIDAY SYSTEM TESTS FAILED!")
            return False

def main():
    print("🚀 Starting Shift Roster & Pay Calculator API Tests")
    print("🎯 FOCUS: Testing Roster Template System for Saving and Loading Monthly Patterns")
    print("=" * 80)
    
    tester = ShiftRosterAPITester()
    
    # Run basic setup tests first
    basic_tests = [
        tester.test_health_check,
        tester.test_get_staff,
        tester.test_get_shift_templates,
        tester.test_get_settings,
    ]
    
    # Run ROSTER TEMPLATE SYSTEM tests (PRIORITY)
    template_tests = [
        tester.test_roster_template_system,
        tester.test_roster_template_edge_cases,
    ]
    
    # Run other tests
    other_tests = [
        tester.test_generate_roster,
        tester.test_get_roster,
        tester.analyze_existing_pay_calculations,
        tester.test_pay_calculations,
        tester.test_roster_assignment,
    ]
    
    print("🔧 Running Basic Setup Tests...")
    for test in basic_tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    print("\n🎯 Running ROSTER TEMPLATE SYSTEM Tests (PRIORITY)...")
    template_results = []
    for test in template_tests:
        try:
            result = test()
            template_results.append(result)
        except Exception as e:
            print(f"❌ Template test failed with exception: {str(e)}")
            template_results.append(False)
    
    print("\n🔧 Running Other Tests...")
    for test in other_tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 80)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    # Special focus on roster template system results
    template_passed = sum(template_results)
    template_total = len(template_results)
    
    print(f"🎯 ROSTER TEMPLATE SYSTEM Results: {template_passed}/{template_total} tests passed")
    
    if template_passed == template_total:
        print("✅ ROSTER TEMPLATE SYSTEM VERIFIED!")
        print("   - Save current roster as template: WORKING")
        print("   - Get all templates: WORKING")
        print("   - Generate roster from template: WORKING")
        print("   - Get specific template: WORKING")
        print("   - Delete template: WORKING")
        print("   - Edge cases handled correctly: WORKING")
    else:
        print("❌ ROSTER TEMPLATE SYSTEM ISSUES DETECTED!")
        print("   - Some template functionality may not be working correctly")
        print("   - Check template save/load logic")
        print("   - Verify template generation preserves patterns")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
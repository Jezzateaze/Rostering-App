import requests
import sys
import json
from datetime import datetime, timedelta

class ShiftRosterAPITester:
    def __init__(self, base_url="https://roster-master-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.staff_data = []
        self.shift_templates = []
        self.roster_entries = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
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
                try:
                    response_data = response.json()
                    if isinstance(response_data, list) and len(response_data) > 0:
                        print(f"   Response: {len(response_data)} items returned")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if response.status_code < 400 else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

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
                "name": "15:00-20:00 shift (extends past 8pm) - CRITICAL TEST",
                "date": "2025-01-06",  # Monday
                "start_time": "15:00",
                "end_time": "20:00",
                "expected_hours": 5.0,
                "expected_rate": 44.50,  # Evening rate
                "expected_pay": 222.50,  # 5 * 44.50
                "shift_type": "EVENING"
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

def main():
    print("🚀 Starting Shift Roster & Pay Calculator API Tests")
    print("=" * 60)
    
    tester = ShiftRosterAPITester()
    
    # Run all tests
    tests = [
        tester.test_health_check,
        tester.test_get_staff,
        tester.test_get_shift_templates,
        tester.test_get_settings,
        tester.test_generate_roster,
        tester.test_get_roster,
        tester.analyze_existing_pay_calculations,
        tester.test_pay_calculations,
        tester.test_roster_assignment,
    ]
    
    # Optional: Test staff creation (commented out to avoid cluttering DB)
    # staff_id = tester.test_create_staff()
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
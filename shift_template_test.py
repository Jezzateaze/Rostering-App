import requests
import sys
import json
from datetime import datetime

class ShiftTemplateEditTester:
    def __init__(self, base_url="https://roster-master-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.shift_templates = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if response.status_code < 400 else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_get_shift_templates(self):
        """Get all shift templates for editing tests"""
        success, response = self.run_test(
            "Get Shift Templates for Editing",
            "GET",
            "api/shift-templates",
            200
        )
        if success:
            self.shift_templates = response
            print(f"   Found {len(response)} shift templates")
            
            # Find Monday Shift 1 for testing
            monday_shift_1 = next((t for t in response if t['name'] == 'Monday Shift 1'), None)
            if monday_shift_1:
                print(f"   Monday Shift 1 current time: {monday_shift_1['start_time']}-{monday_shift_1['end_time']}")
                print(f"   Sleepover: {monday_shift_1['is_sleepover']}")
            else:
                print("   ⚠️  Monday Shift 1 not found")
        return success

    def test_update_shift_template(self):
        """Test updating a shift template (Monday Shift 1 from 07:30-15:30 to 08:00-16:00)"""
        monday_shift_1 = next((t for t in self.shift_templates if t['name'] == 'Monday Shift 1'), None)
        if not monday_shift_1:
            print("❌ Cannot test template update - Monday Shift 1 not found")
            return False

        # Store original times for restoration
        original_start = monday_shift_1['start_time']
        original_end = monday_shift_1['end_time']
        
        print(f"   Original times: {original_start}-{original_end}")
        print(f"   Updating to: 08:00-16:00")

        # Update the template
        updated_template = {
            **monday_shift_1,
            "start_time": "08:00",
            "end_time": "16:00"
        }

        success, response = self.run_test(
            "Update Monday Shift 1 Template (08:00-16:00)",
            "PUT",
            f"api/shift-templates/{monday_shift_1['id']}",
            200,
            data=updated_template
        )

        if success:
            print(f"   Updated template: {response['start_time']}-{response['end_time']}")
            
            # Verify the change persisted
            verify_success, verify_response = self.run_test(
                "Verify Template Update Persisted",
                "GET",
                "api/shift-templates",
                200
            )
            
            if verify_success:
                updated_monday_shift = next((t for t in verify_response if t['name'] == 'Monday Shift 1'), None)
                if updated_monday_shift:
                    if updated_monday_shift['start_time'] == "08:00" and updated_monday_shift['end_time'] == "16:00":
                        print(f"   ✅ Template update verified: {updated_monday_shift['start_time']}-{updated_monday_shift['end_time']}")
                    else:
                        print(f"   ❌ Template update not persisted correctly")
                        success = False

            # Restore original times
            restore_template = {
                **monday_shift_1,
                "start_time": original_start,
                "end_time": original_end
            }
            
            restore_success, _ = self.run_test(
                "Restore Original Template Times",
                "PUT",
                f"api/shift-templates/{monday_shift_1['id']}",
                200,
                data=restore_template
            )
            
            if restore_success:
                print(f"   ✅ Original times restored: {original_start}-{original_end}")

        return success

    def test_sleepover_toggle(self):
        """Test toggling sleepover status on a template"""
        # Find a non-sleepover shift to test with
        test_shift = next((t for t in self.shift_templates 
                          if not t['is_sleepover'] and 'Shift 2' in t['name']), None)
        
        if not test_shift:
            print("❌ Cannot test sleepover toggle - suitable shift not found")
            return False

        original_sleepover = test_shift['is_sleepover']
        print(f"   Testing with {test_shift['name']}")
        print(f"   Original sleepover status: {original_sleepover}")

        # Toggle sleepover status
        updated_template = {
            **test_shift,
            "is_sleepover": not original_sleepover
        }

        success, response = self.run_test(
            f"Toggle Sleepover Status for {test_shift['name']}",
            "PUT",
            f"api/shift-templates/{test_shift['id']}",
            200,
            data=updated_template
        )

        if success:
            print(f"   Updated sleepover status: {response['is_sleepover']}")
            
            # Restore original status
            restore_template = {
                **test_shift,
                "is_sleepover": original_sleepover
            }
            
            restore_success, _ = self.run_test(
                "Restore Original Sleepover Status",
                "PUT",
                f"api/shift-templates/{test_shift['id']}",
                200,
                data=restore_template
            )
            
            if restore_success:
                print(f"   ✅ Original sleepover status restored: {original_sleepover}")

        return success

    def test_individual_shift_time_editing(self):
        """Test editing individual shift times in roster entries"""
        # Get current month roster
        current_month = datetime.now().strftime("%Y-%m")
        success, roster_response = self.run_test(
            f"Get Roster for Individual Shift Editing",
            "GET",
            f"api/roster?month={current_month}",
            200
        )
        
        if not success or not roster_response:
            print("❌ Cannot test individual shift editing - no roster data")
            return False

        # Find a Friday shift to test (15:00-20:00 to 14:00-19:00)
        friday_shift = None
        for entry in roster_response:
            entry_date = datetime.strptime(entry['date'], "%Y-%m-%d")
            if (entry_date.weekday() == 4 and  # Friday
                entry['start_time'] == '15:00' and 
                entry['end_time'] == '20:00'):
                friday_shift = entry
                break

        if not friday_shift:
            print("❌ Cannot test individual shift editing - suitable Friday shift not found")
            return False

        print(f"   Testing with Friday shift: {friday_shift['date']} {friday_shift['start_time']}-{friday_shift['end_time']}")
        print(f"   Original pay: ${friday_shift['total_pay']}")

        # Update shift times (15:00-20:00 to 14:00-19:00)
        updated_shift = {
            **friday_shift,
            "start_time": "14:00",
            "end_time": "19:00"
        }

        success, response = self.run_test(
            "Update Individual Friday Shift Times (14:00-19:00)",
            "PUT",
            f"api/roster/{friday_shift['id']}",
            200,
            data=updated_shift
        )

        if success:
            print(f"   Updated shift times: {response['start_time']}-{response['end_time']}")
            print(f"   Updated hours: {response['hours_worked']}")
            print(f"   Updated pay: ${response['total_pay']}")
            
            # Verify evening rate applies (should be $44.50/hr for 5 hours = $222.50)
            expected_pay = 5.0 * 44.50  # 5 hours at evening rate
            actual_pay = response['total_pay']
            
            if abs(actual_pay - expected_pay) < 0.01:
                print(f"   ✅ Evening rate applied correctly: ${actual_pay}")
            else:
                print(f"   ❌ Evening rate not applied correctly: got ${actual_pay}, expected ${expected_pay}")

            # Restore original times
            restore_shift = {
                **friday_shift,
                "start_time": "15:00",
                "end_time": "20:00"
            }
            
            restore_success, _ = self.run_test(
                "Restore Original Friday Shift Times",
                "PUT",
                f"api/roster/{friday_shift['id']}",
                200,
                data=restore_shift
            )
            
            if restore_success:
                print(f"   ✅ Original shift times restored")

        return success

def main():
    print("🚀 Starting Shift Template Editing Tests")
    print("=" * 60)
    
    tester = ShiftTemplateEditTester()
    
    # Run template editing tests
    tests = [
        tester.test_get_shift_templates,
        tester.test_update_shift_template,
        tester.test_sleepover_toggle,
        tester.test_individual_shift_time_editing,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Template Editing Tests: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All template editing tests passed!")
        return 0
    else:
        print("⚠️  Some template editing tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
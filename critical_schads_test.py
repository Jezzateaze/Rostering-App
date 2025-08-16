#!/usr/bin/env python3
"""
Critical SCHADS Award Pay Calculation Test
Focuses on the specific issues mentioned in the review request:
1. Evening shift boundary rule (15:00-20:00 should be EVENING, not DAY)
2. Weekend rate accuracy 
3. Day of week calculations
"""

import requests
import sys
from datetime import datetime

class CriticalSCHADSTest:
    def __init__(self, base_url="https://roster-master-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.critical_failures = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                return True, response.json()
            else:
                print(f"❌ HTTP Error - Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            return False, {}

    def test_critical_evening_shift_boundary(self):
        """Test the critical 15:00-20:00 evening shift boundary rule"""
        print("\n" + "="*80)
        print("🎯 CRITICAL TEST A: Evening Shift Boundary Rule (15:00-20:00)")
        print("Expected: Should be EVENING rate ($44.50/hr), NOT day rate ($42.00/hr)")
        print("="*80)

        # Test the exact scenario from the review request
        test_entry = {
            "id": "",
            "date": "2025-08-01",  # Friday
            "shift_template_id": "test-critical-evening",
            "start_time": "15:00",
            "end_time": "20:00",
            "is_sleepover": False,
            "is_public_holiday": False,
            "staff_id": None,
            "staff_name": None,
            "hours_worked": 0.0,
            "base_pay": 0.0,
            "sleepover_allowance": 0.0,
            "total_pay": 0.0
        }

        success, response = self.run_test(
            "Create 15:00-20:00 Friday shift",
            "POST",
            "api/roster",
            200,
            data=test_entry
        )

        if success:
            hours = response.get('hours_worked', 0)
            total_pay = response.get('total_pay', 0)
            base_pay = response.get('base_pay', 0)
            
            print(f"   Hours worked: {hours}")
            print(f"   Base pay: ${base_pay}")
            print(f"   Total pay: ${total_pay}")
            
            # Expected: 5 hours × $44.50 = $222.50 (evening rate)
            expected_evening_pay = 5.0 * 44.50  # $222.50
            expected_day_pay = 5.0 * 42.00      # $210.00
            
            if abs(total_pay - expected_evening_pay) < 0.01:
                print(f"   ✅ CORRECT: Using evening rate - ${total_pay} (expected ${expected_evening_pay})")
                print(f"   ✅ SCHADS Rule Applied: Shift extends past 8:00pm → Evening rate")
                return True
            elif abs(total_pay - expected_day_pay) < 0.01:
                print(f"   ❌ INCORRECT: Using day rate - ${total_pay} (should be ${expected_evening_pay})")
                print(f"   ❌ SCHADS Rule NOT Applied: 15:00-20:00 extends past 8:00pm → Should be evening rate")
                self.critical_failures.append("Evening shift boundary rule (15:00-20:00)")
                return False
            else:
                print(f"   ❌ UNEXPECTED: Pay amount ${total_pay} doesn't match day (${expected_day_pay}) or evening (${expected_evening_pay}) rates")
                self.critical_failures.append("Evening shift boundary rule - unexpected pay amount")
                return False
        else:
            self.critical_failures.append("Evening shift boundary rule - API call failed")
            return False

    def test_weekend_rates(self):
        """Test weekend rate accuracy"""
        print("\n" + "="*80)
        print("🎯 CRITICAL TEST B: Weekend Rate Accuracy")
        print("Expected: Saturday $57.50/hr, Sunday $74.00/hr")
        print("="*80)

        weekend_tests = [
            {
                "name": "Saturday 8-hour shift",
                "date": "2025-08-02",  # Saturday
                "expected_rate": 57.50,
                "expected_total": 460.00  # 8 × $57.50
            },
            {
                "name": "Sunday 8-hour shift", 
                "date": "2025-08-03",  # Sunday
                "expected_rate": 74.00,
                "expected_total": 592.00  # 8 × $74.00
            }
        ]

        weekend_passed = 0
        for test in weekend_tests:
            test_entry = {
                "id": "",
                "date": test["date"],
                "shift_template_id": "test-weekend",
                "start_time": "07:30",
                "end_time": "15:30",
                "is_sleepover": False,
                "is_public_holiday": False,
                "staff_id": None,
                "staff_name": None,
                "hours_worked": 0.0,
                "base_pay": 0.0,
                "sleepover_allowance": 0.0,
                "total_pay": 0.0
            }

            success, response = self.run_test(
                f"Create {test['name']}",
                "POST",
                "api/roster",
                200,
                data=test_entry
            )

            if success:
                total_pay = response.get('total_pay', 0)
                print(f"   {test['name']}: ${total_pay} (expected ${test['expected_total']})")
                
                if abs(total_pay - test['expected_total']) < 0.01:
                    print(f"   ✅ CORRECT: Weekend rate applied")
                    weekend_passed += 1
                else:
                    print(f"   ❌ INCORRECT: Wrong weekend rate")
                    self.critical_failures.append(f"Weekend rate - {test['name']}")

        return weekend_passed == len(weekend_tests)

    def test_day_of_week_logic(self):
        """Test day of week calculations - Monday should be weekday, not Sunday"""
        print("\n" + "="*80)
        print("🎯 CRITICAL TEST C: Day of Week Logic")
        print("Expected: Monday uses weekday rates, NOT Sunday rates")
        print("="*80)

        # Test specific dates from August 2025 as mentioned in review request
        day_tests = [
            {
                "name": "Friday Aug 1",
                "date": "2025-08-01",
                "expected_type": "weekday",
                "expected_day_rate": 42.00
            },
            {
                "name": "Saturday Aug 2", 
                "date": "2025-08-02",
                "expected_type": "saturday",
                "expected_day_rate": 57.50
            },
            {
                "name": "Sunday Aug 3",
                "date": "2025-08-03", 
                "expected_type": "sunday",
                "expected_day_rate": 74.00
            },
            {
                "name": "Monday Aug 4",
                "date": "2025-08-04",
                "expected_type": "weekday", 
                "expected_day_rate": 42.00  # Should be weekday, NOT Sunday rate (74.00)
            }
        ]

        day_logic_passed = 0
        for test in day_tests:
            test_entry = {
                "id": "",
                "date": test["date"],
                "shift_template_id": "test-day-logic",
                "start_time": "07:30",
                "end_time": "15:30",  # 8-hour day shift
                "is_sleepover": False,
                "is_public_holiday": False,
                "staff_id": None,
                "staff_name": None,
                "hours_worked": 0.0,
                "base_pay": 0.0,
                "sleepover_allowance": 0.0,
                "total_pay": 0.0
            }

            success, response = self.run_test(
                f"Create {test['name']} day shift",
                "POST", 
                "api/roster",
                200,
                data=test_entry
            )

            if success:
                total_pay = response.get('total_pay', 0)
                expected_pay = 8.0 * test['expected_day_rate']
                
                print(f"   {test['name']}: ${total_pay} (expected ${expected_pay} for {test['expected_type']})")
                
                if abs(total_pay - expected_pay) < 0.01:
                    print(f"   ✅ CORRECT: {test['expected_type']} rate applied")
                    day_logic_passed += 1
                else:
                    print(f"   ❌ INCORRECT: Wrong day type rate")
                    if test['name'] == "Monday Aug 4" and abs(total_pay - (8.0 * 74.00)) < 0.01:
                        print(f"   ❌ CRITICAL: Monday is using Sunday rate (${74.00}/hr) instead of weekday rate (${42.00}/hr)")
                    self.critical_failures.append(f"Day of week logic - {test['name']}")

        return day_logic_passed == len(day_tests)

    def run_all_critical_tests(self):
        """Run all critical tests and provide summary"""
        print("🚀 CRITICAL SCHADS AWARD PAY CALCULATION VERIFICATION")
        print("Testing the specific issues mentioned in the review request")
        print("="*80)

        # Run critical tests
        test_a_passed = self.test_critical_evening_shift_boundary()
        test_b_passed = self.test_weekend_rates()  
        test_c_passed = self.test_day_of_week_logic()

        # Summary
        print("\n" + "="*80)
        print("📊 CRITICAL TEST RESULTS SUMMARY")
        print("="*80)
        
        print(f"🎯 Test A - Evening Shift Boundary (15:00-20:00): {'✅ PASSED' if test_a_passed else '❌ FAILED'}")
        print(f"🎯 Test B - Weekend Rate Accuracy: {'✅ PASSED' if test_b_passed else '❌ FAILED'}")
        print(f"🎯 Test C - Day of Week Logic: {'✅ PASSED' if test_c_passed else '❌ FAILED'}")
        
        total_critical_passed = sum([test_a_passed, test_b_passed, test_c_passed])
        print(f"\n📈 Overall Critical Tests: {total_critical_passed}/3 passed")
        
        if self.critical_failures:
            print(f"\n🚨 CRITICAL FAILURES DETECTED:")
            for i, failure in enumerate(self.critical_failures, 1):
                print(f"   {i}. {failure}")
            print(f"\n⚠️  These issues need to be fixed before the SCHADS Award compliance is complete.")
        else:
            print(f"\n🎉 ALL CRITICAL TESTS PASSED!")
            print(f"✅ SCHADS Award pay calculation fixes are working correctly.")

        return total_critical_passed == 3

def main():
    tester = CriticalSCHADSTest()
    success = tester.run_all_critical_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
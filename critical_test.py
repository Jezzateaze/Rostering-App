#!/usr/bin/env python3
"""
Critical test for the 15:00-20:00 shift classification bug.
This test specifically verifies that shifts ending AT 8:00 PM are classified as EVENING rate.
"""

import requests
import sys
from datetime import datetime

API_BASE_URL = "https://shiftplanner-1.preview.emergentagent.com"

def test_critical_15_20_scenario():
    """Test the exact 15:00-20:00 scenario that was failing"""
    print("🎯 CRITICAL TEST: 15:00-20:00 shift classification")
    print("=" * 50)
    
    # Test data for the exact scenario from the bug report
    test_case = {
        "date": "2025-08-01",  # Friday
        "start_time": "15:00",
        "end_time": "20:00",
        "expected_hours": 5.0,
        "expected_rate": 44.50,  # Evening rate
        "expected_pay": 222.50,  # 5 × $44.50
        "description": "15:00-20:00 Friday shift (ends AT 8:00 PM)"
    }
    
    print(f"Testing: {test_case['description']}")
    print(f"Expected: {test_case['expected_hours']} hours × ${test_case['expected_rate']}/hr = ${test_case['expected_pay']}")
    
    # Create roster entry
    roster_entry = {
        "id": "",  # Will be auto-generated
        "date": test_case["date"],
        "shift_template_id": "test-critical",
        "start_time": test_case["start_time"],
        "end_time": test_case["end_time"],
        "is_sleepover": False,
        "is_public_holiday": False,
        "staff_id": None,
        "staff_name": None,
        "hours_worked": 0.0,
        "base_pay": 0.0,
        "sleepover_allowance": 0.0,
        "total_pay": 0.0
    }
    
    try:
        # Create the roster entry via API
        response = requests.post(
            f"{API_BASE_URL}/api/roster",
            json=roster_entry,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            print(f"❌ API call failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        result = response.json()
        
        # Extract results
        hours_worked = result.get('hours_worked', 0)
        total_pay = result.get('total_pay', 0)
        base_pay = result.get('base_pay', 0)
        
        print(f"\nResults:")
        print(f"  Hours worked: {hours_worked}")
        print(f"  Base pay: ${base_pay}")
        print(f"  Total pay: ${total_pay}")
        
        # Verify calculations
        hours_correct = abs(hours_worked - test_case['expected_hours']) < 0.1
        pay_correct = abs(total_pay - test_case['expected_pay']) < 0.01
        
        print(f"\nVerification:")
        print(f"  Hours correct: {'✅' if hours_correct else '❌'} (got {hours_worked}, expected {test_case['expected_hours']})")
        print(f"  Pay correct: {'✅' if pay_correct else '❌'} (got ${total_pay}, expected ${test_case['expected_pay']})")
        
        if hours_correct and pay_correct:
            print(f"\n🎉 SUCCESS: 15:00-20:00 shift now correctly classified as EVENING rate!")
            print(f"   The fix is working - shifts ending AT 8:00 PM use evening rate (${test_case['expected_rate']}/hr)")
            return True
        else:
            print(f"\n❌ FAILURE: 15:00-20:00 shift still not correctly classified")
            if not pay_correct:
                actual_rate = total_pay / hours_worked if hours_worked > 0 else 0
                print(f"   Actual rate: ${actual_rate:.2f}/hr (should be ${test_case['expected_rate']}/hr)")
                if actual_rate == 42.00:
                    print(f"   🚨 Still using DAY rate instead of EVENING rate!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        return False

def test_boundary_scenarios():
    """Test edge cases around the 8:00 PM boundary"""
    print(f"\n🔍 Testing boundary scenarios around 8:00 PM")
    print("=" * 50)
    
    boundary_tests = [
        {
            "name": "15:00-19:59 (ends 1 min before 8pm)",
            "start": "15:00", "end": "19:59",
            "expected_rate": 42.00, "expected_type": "DAY"
        },
        {
            "name": "15:00-20:00 (ends exactly at 8pm)", 
            "start": "15:00", "end": "20:00",
            "expected_rate": 44.50, "expected_type": "EVENING"
        },
        {
            "name": "15:00-20:01 (ends 1 min after 8pm)",
            "start": "15:00", "end": "20:01", 
            "expected_rate": 44.50, "expected_type": "EVENING"
        }
    ]
    
    all_passed = True
    
    for test in boundary_tests:
        print(f"\nTesting: {test['name']}")
        
        # Calculate expected hours and pay
        start_hour, start_min = map(int, test['start'].split(':'))
        end_hour, end_min = map(int, test['end'].split(':'))
        
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        hours = (end_minutes - start_minutes) / 60.0
        expected_pay = hours * test['expected_rate']
        
        roster_entry = {
            "id": "",
            "date": "2025-08-01",  # Friday
            "shift_template_id": f"boundary-test-{test['start']}-{test['end']}",
            "start_time": test['start'],
            "end_time": test['end'],
            "is_sleepover": False,
            "is_public_holiday": False,
            "staff_id": None,
            "staff_name": None,
            "hours_worked": 0.0,
            "base_pay": 0.0,
            "sleepover_allowance": 0.0,
            "total_pay": 0.0
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/roster",
                json=roster_entry,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                actual_pay = result.get('total_pay', 0)
                actual_hours = result.get('hours_worked', 0)
                actual_rate = actual_pay / actual_hours if actual_hours > 0 else 0
                
                rate_correct = abs(actual_rate - test['expected_rate']) < 0.01
                
                print(f"  Expected: {hours:.2f}h × ${test['expected_rate']}/hr = ${expected_pay:.2f} ({test['expected_type']})")
                print(f"  Actual:   {actual_hours:.2f}h × ${actual_rate:.2f}/hr = ${actual_pay:.2f} {'✅' if rate_correct else '❌'}")
                
                if not rate_correct:
                    all_passed = False
            else:
                print(f"  ❌ API call failed: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"  ❌ Test failed: {str(e)}")
            all_passed = False
    
    return all_passed

def main():
    print("🚀 Critical Test: 15:00-20:00 Shift Classification Fix")
    print("Testing the specific bug reported by main agent")
    print("=" * 60)
    
    # Test the critical scenario
    critical_passed = test_critical_15_20_scenario()
    
    # Test boundary scenarios
    boundary_passed = test_boundary_scenarios()
    
    print(f"\n" + "=" * 60)
    print(f"📊 FINAL RESULTS:")
    print(f"  Critical 15:00-20:00 test: {'✅ PASSED' if critical_passed else '❌ FAILED'}")
    print(f"  Boundary scenarios: {'✅ PASSED' if boundary_passed else '❌ FAILED'}")
    
    if critical_passed and boundary_passed:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"   The 15:00-20:00 shift classification bug has been FIXED!")
        print(f"   Shifts ending AT 8:00 PM now correctly use EVENING rate ($44.50/hr)")
        return 0
    else:
        print(f"\n❌ SOME TESTS FAILED!")
        print(f"   The bug may still exist or there are other issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
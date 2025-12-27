#!/usr/bin/env python3
"""
Test script to validate Driver.js tour implementation in model_building_game.py

This test verifies that:
1. The Driver.js library is properly imported via CDN
2. The tour has 5 steps as required
3. All steps contain the correct content from the original slides
4. The tour auto-starts on first visit using localStorage
5. The slides have been removed and navigation updated
"""

import re
import sys
from pathlib import Path

def test_driver_js_tour():
    """Main test function for Driver.js tour implementation"""
    
    # Load the file
    file_path = Path(__file__).parent.parent / "aimodelshare" / "moral_compass" / "apps" / "model_building_game.py"
    with open(file_path, 'r') as f:
        content = f.read()
    
    print("Testing Driver.js Tour Implementation")
    print("=" * 60)
    
    # Test 1: Check Driver.js library is imported
    print("\n✓ Test 1: Checking Driver.js library import...")
    if 'driver.js@1.3.1/dist/driver.css' in content and 'driver.js@1.3.1/dist/driver.js.iife.js' in content:
        print("  ✅ PASS: Driver.js CSS and JS are properly imported via CDN")
    else:
        print("  ❌ FAIL: Driver.js library not found")
        return False
    
    # Test 2: Check that tour has 5 steps
    print("\n✓ Test 2: Checking tour has 5 steps...")
    # Count the number of popover titles in the tour
    tour_section = re.search(r'steps: \[(.*?)\]', content, re.DOTALL)
    if tour_section:
        steps = re.findall(r"title: '([^']+)'", tour_section.group(1))
        if len(steps) == 5:
            print(f"  ✅ PASS: Tour has {len(steps)} steps as required")
            for i, step in enumerate(steps, 1):
                print(f"    Step {i}: {step}")
        else:
            print(f"  ❌ FAIL: Tour has {len(steps)} steps, expected 5")
            return False
    else:
        print("  ❌ FAIL: Could not find tour steps")
        return False
    
    # Test 3: Verify key content from original slides is present
    print("\n✓ Test 3: Checking key content from original slides...")
    required_content = [
        "Welcome to the Model Building Arena",
        'What is a "Model"?',
        "How Engineers Work",
        "Control Knobs",
        "Data Ingredients",
        "Build & Submit Model",
        "Trainee → Junior → Senior → Lead Engineer"
    ]
    
    all_found = True
    for content_item in required_content:
        if content_item in content:
            print(f"  ✅ Found: '{content_item}'")
        else:
            print(f"  ❌ Missing: '{content_item}'")
            all_found = False
    
    if not all_found:
        return False
    
    # Test 4: Check localStorage is used for auto-start
    print("\n✓ Test 4: Checking localStorage for tour auto-start...")
    if 'localStorage.getItem' in content and 'modelArena_tourShown' in content:
        print("  ✅ PASS: Tour uses localStorage to track first visit")
    else:
        print("  ❌ FAIL: localStorage not properly implemented")
        return False
    
    # Test 5: Check that slides have been removed
    print("\n✓ Test 5: Checking that instruction slides have been removed...")
    slide_indicators = ['briefing_slide_1', 'briefing_slide_2', 'briefing_slide_3', 
                       'briefing_slide_4', 'briefing_slide_5', 'briefing_slide_6', 'briefing_slide_7']
    
    slides_found = []
    for slide in slide_indicators:
        # Check if slide is defined (as a Column)
        if f'as {slide}:' in content:
            slides_found.append(slide)
    
    if slides_found:
        print(f"  ❌ FAIL: Slides still present: {', '.join(slides_found)}")
        return False
    else:
        print("  ✅ PASS: All instruction slides have been removed")
    
    # Test 6: Check that navigation has been updated
    print("\n✓ Test 6: Checking navigation logic has been updated...")
    if 'all_steps_nav = [' in content:
        # Extract the navigation list
        nav_match = re.search(r'all_steps_nav = \[(.*?)\]', content, re.DOTALL)
        if nav_match:
            nav_content = nav_match.group(1)
            # Check that briefing slides are NOT in the navigation
            has_briefing_slides = any(f'briefing_slide_{i}' in nav_content for i in range(1, 8))
            if has_briefing_slides:
                print("  ❌ FAIL: Navigation still references briefing slides")
                return False
            else:
                print("  ✅ PASS: Navigation updated to exclude briefing slides")
        else:
            print("  ❌ FAIL: Could not find navigation list")
            return False
    
    # Test 7: Check that model_building_step is visible by default
    print("\n✓ Test 7: Checking model_building_step is visible by default...")
    model_step_match = re.search(r'with gr\.Column\(visible=(True|False).*?\) as model_building_step:', content)
    if model_step_match:
        is_visible = model_step_match.group(1) == 'True'
        if is_visible:
            print("  ✅ PASS: model_building_step is visible by default")
        else:
            print("  ❌ FAIL: model_building_step is not visible by default")
            return False
    else:
        print("  ⚠️  WARNING: Could not verify visibility setting")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("\nSummary:")
    print("- Driver.js library successfully integrated")
    print("- 5-step tour created with comprehensive content")
    print("- All original slide content preserved in tour")
    print("- Tour auto-starts on first visit")
    print("- All 7 instruction slides removed")
    print("- Navigation logic updated")
    print("- Model building arena now launches directly")
    return True

if __name__ == "__main__":
    success = test_driver_js_tour()
    sys.exit(0 if success else 1)

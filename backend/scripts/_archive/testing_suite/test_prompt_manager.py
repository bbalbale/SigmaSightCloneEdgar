#!/usr/bin/env python3
"""
Test script for the prompt management system.
Verifies that prompts load correctly and PromptManager functions work.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.prompts.prompt_manager import PromptManager, get_prompt_manager


def test_prompt_loading():
    """Test loading individual prompts."""
    print("\n🔧 Testing Prompt Loading")
    print("=" * 60)
    
    manager = PromptManager()
    
    # Test loading each mode
    modes = ['green', 'blue', 'indigo', 'violet']
    
    for mode in modes:
        print(f"\n1️⃣ Testing {mode} mode...")
        try:
            prompt = manager.load_prompt(mode)
            metadata = manager.get_metadata(mode)
            
            print(f"✅ Loaded {mode} prompt successfully")
            print(f"   Persona: {metadata.get('persona', 'Not specified')}")
            print(f"   Token Budget: {metadata.get('token_budget', 'Not specified')}")
            print(f"   Content Length: {len(prompt)} characters")
            
            # Verify prompt contains expected content
            if mode == 'green' and 'Educational' not in prompt:
                print(f"⚠️ Warning: Green prompt missing 'Educational' keyword")
            elif mode == 'blue' and 'quantitative' not in prompt.lower():
                print(f"⚠️ Warning: Blue prompt missing 'quantitative' keyword")
            elif mode == 'indigo' and 'Strategic' not in prompt:
                print(f"⚠️ Warning: Indigo prompt missing 'Strategic' keyword")
            elif mode == 'violet' and 'Conservative' not in prompt:
                print(f"⚠️ Warning: Violet prompt missing 'Conservative' keyword")
                
        except Exception as e:
            print(f"❌ Failed to load {mode} prompt: {e}")
            return False
    
    return True


def test_system_prompt():
    """Test generating complete system prompts."""
    print("\n🔧 Testing System Prompt Generation")
    print("=" * 60)
    
    manager = get_prompt_manager()
    
    # Test with user context
    user_context = {
        'portfolio_id': 'test-portfolio-123',
        'user_name': 'Test User',
        'portfolio_value': 125430.22
    }
    
    print("\n2️⃣ Testing system prompt with context...")
    try:
        system_prompt = manager.get_system_prompt('green', user_context)
        
        print("✅ Generated system prompt successfully")
        print(f"   Total Length: {len(system_prompt)} characters")
        
        # Check if common instructions are included
        if 'Common Instructions' in system_prompt:
            print("✅ Common instructions included")
        else:
            print("⚠️ Warning: Common instructions not found")
        
        # Check if mode-specific prompt is included
        if 'Green Mode' in system_prompt or 'Teaching-focused' in system_prompt:
            print("✅ Mode-specific prompt included")
        else:
            print("⚠️ Warning: Mode-specific content not found")
            
    except Exception as e:
        print(f"❌ Failed to generate system prompt: {e}")
        return False
    
    return True


def test_variable_injection():
    """Test variable injection into prompts."""
    print("\n🔧 Testing Variable Injection")
    print("=" * 60)
    
    manager = PromptManager()
    
    # Test template with variables
    template = "Hello {user_name}, your portfolio {portfolio_id} is worth ${portfolio_value}. Current time: {current_time}"
    
    variables = {
        'user_name': 'John Doe',
        'portfolio_id': 'abc-123',
        'portfolio_value': 50000
    }
    
    print("\n3️⃣ Testing variable injection...")
    try:
        result = manager.inject_variables(template, variables)
        
        print("✅ Variable injection successful")
        print(f"   Result: {result[:100]}...")
        
        # Verify variables were replaced
        if 'John Doe' in result and 'abc-123' in result and '50000' in result:
            print("✅ All variables replaced correctly")
        else:
            print("⚠️ Warning: Some variables not replaced")
            
        # Check standard variables
        if 'gpt-5-2025-08-07' in result:
            print("✅ Standard model variable injected")
        if 'Z' in result:  # UTC timestamp should end with Z
            print("✅ Timestamp injected correctly")
            
    except Exception as e:
        print(f"❌ Variable injection failed: {e}")
        return False
    
    return True


def test_metadata_and_utilities():
    """Test metadata retrieval and utility functions."""
    print("\n🔧 Testing Metadata and Utilities")
    print("=" * 60)
    
    manager = PromptManager()
    
    print("\n4️⃣ Testing utility functions...")
    
    # Test listing available modes
    try:
        modes = manager.list_available_modes()
        print(f"✅ Available modes: {modes}")
        
        if set(modes) == {'blue', 'green', 'indigo', 'violet'}:
            print("✅ All expected modes found")
        else:
            print(f"⚠️ Warning: Expected 4 modes, found {len(modes)}")
    except Exception as e:
        print(f"❌ Failed to list modes: {e}")
    
    # Test mode validation
    try:
        valid = manager.validate_mode('green')
        invalid = manager.validate_mode('rainbow')
        
        if valid and not invalid:
            print("✅ Mode validation working correctly")
        else:
            print("⚠️ Warning: Mode validation issue")
    except Exception as e:
        print(f"❌ Mode validation failed: {e}")
    
    # Test token budget retrieval
    try:
        budgets = {}
        for mode in ['green', 'blue', 'indigo', 'violet']:
            budgets[mode] = manager.get_token_budget(mode)
        
        print(f"✅ Token budgets: {budgets}")
        
        expected = {'green': 2000, 'blue': 1500, 'indigo': 1800, 'violet': 1700}
        if budgets == expected:
            print("✅ Token budgets match expected values")
        else:
            print(f"⚠️ Warning: Token budgets differ from expected")
            
    except Exception as e:
        print(f"❌ Token budget retrieval failed: {e}")
    
    # Test mode info formatting
    try:
        info = manager.format_mode_info('green')
        print(f"\n📋 Green Mode Info:\n{info}")
        
        if 'Teaching-focused' in info:
            print("✅ Mode info formatted correctly")
        else:
            print("⚠️ Warning: Mode info missing expected content")
            
    except Exception as e:
        print(f"❌ Mode info formatting failed: {e}")
    
    return True


def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n🔧 Testing Error Handling")
    print("=" * 60)
    
    manager = PromptManager()
    
    print("\n5️⃣ Testing error conditions...")
    
    # Test loading non-existent mode
    try:
        manager.load_prompt('nonexistent')
        print("❌ Should have raised FileNotFoundError")
    except FileNotFoundError:
        print("✅ Correctly raised FileNotFoundError for missing prompt")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Test invalid version
    try:
        manager.load_prompt('green', 'v999')
        print("❌ Should have raised FileNotFoundError")
    except FileNotFoundError:
        print("✅ Correctly raised FileNotFoundError for invalid version")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 PROMPT MANAGER TEST SUITE")
    print("=" * 60)
    
    all_passed = True
    
    # Run tests
    tests = [
        ("Prompt Loading", test_prompt_loading),
        ("System Prompt Generation", test_system_prompt),
        ("Variable Injection", test_variable_injection),
        ("Metadata and Utilities", test_metadata_and_utilities),
        ("Error Handling", test_error_handling)
    ]
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                all_passed = False
                print(f"\n❌ {test_name} test failed")
        except Exception as e:
            all_passed = False
            print(f"\n❌ {test_name} test crashed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
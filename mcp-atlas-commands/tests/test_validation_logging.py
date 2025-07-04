#!/usr/bin/env python3
"""
Test script to verify that Pydantic validation errors are now logged at ERROR level.
This script simulates a validation error to ensure the logging improvements work.
"""

import sys
import tempfile
from pathlib import Path

# Add PANTHER to path
panther_path = Path(__file__).parent / "REPOS" / "PANTHER"
sys.path.insert(0, str(panther_path))

try:
    from panther.config.core.components.validators import PydanticValidator
    from panther.config.core.models.base import BaseUnifiedModel
    from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
    
    print("✅ Successfully imported PANTHER validation components")
    
    # Create a test model with validation constraints
    class TestConfig(BaseUnifiedModel):
        name: str = Field(..., min_length=3)
        port: int = Field(..., ge=1, le=65535)
        enabled: bool = True
    
    # Create validator
    validator = PydanticValidator()
    
    print("🧪 Testing Pydantic validation error logging...")
    
    # Test case 1: Valid configuration (should not produce errors)
    print("\n--- Test Case 1: Valid Configuration ---")
    valid_config = TestConfig(name="test", port=8080, enabled=True)
    result = validator.validate(valid_config)
    print(f"✅ Valid config result: is_valid={result.is_valid}, errors={len(result.errors)}")
    
    # Test case 2: Invalid configuration (should produce ERROR logs)
    print("\n--- Test Case 2: Invalid Configuration ---")
    try:
        # This should fail validation - name too short, port out of range
        invalid_data = {"name": "ab", "port": 70000, "enabled": "not_a_boolean"}
        invalid_config = TestConfig(**invalid_data)
    except PydanticValidationError as e:
        print(f"🔍 Caught PydanticValidationError with {len(e.errors())} errors:")
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error['loc'])
            print(f"   - {field_path}: {error['msg']}")
        
        # Now test our validator's handling of this
        print("\n🧪 Testing validator error handling...")
        
        # Create a mock config that will trigger validation error
        class MockInvalidConfig(BaseUnifiedModel):
            @classmethod
            def model_validate(cls, obj):
                # Simulate the validation error
                raise PydanticValidationError.from_exception_data("MockInvalidConfig", [
                    {
                        'type': 'string_too_short',
                        'loc': ('name',),
                        'msg': 'String should have at least 3 characters',
                        'input': 'ab'
                    },
                    {
                        'type': 'greater_than_equal',
                        'loc': ('port',),
                        'msg': 'Input should be greater than or equal to 1',
                        'input': 70000
                    }
                ])
        
        mock_config = MockInvalidConfig()
        result = validator.validate(mock_config)
        print(f"📊 Validation result: is_valid={result.is_valid}, errors={len(result.errors)}")
        
        for error in result.errors:
            print(f"   ❌ {error}")
            
        print("\n✅ Test completed! Check the logs above for ERROR level messages.")
        print("🔍 You should see 'Pydantic validation failed' and individual field errors logged at ERROR level.")
        
except ImportError as e:
    print(f"❌ Failed to import PANTHER components: {e}")
    print("💡 Make sure you're running this from the correct directory and PANTHER is properly set up")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
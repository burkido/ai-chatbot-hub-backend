import pytest
from unittest.mock import Mock

from app.core.llm.assistant_config import (
    get_assistant_config, 
    validate_assistant_config,
    register_assistant_type,
    get_available_assistant_types,
    get_config_summary,
    ASSISTANT_TYPE_DOCTOR,
    ASSISTANT_TYPE_GENERAL,
    ASSISTANT_CONFIGS
)


class TestAssistantConfig:
    def test_get_assistant_config_valid(self):
        """Test getting valid assistant configuration"""
        config = get_assistant_config(ASSISTANT_TYPE_DOCTOR)
        
        assert "name" in config
        assert "system_prompt" in config
        assert "temperature" in config
        assert config["name"] == "Doctor Assistant"
        assert isinstance(config["system_prompt"], str)
        assert len(config["system_prompt"]) > 0
        assert isinstance(config["temperature"], (int, float))
    
    def test_get_assistant_config_case_insensitive(self):
        """Test assistant config is case insensitive"""
        config1 = get_assistant_config("DOCTOR")
        config2 = get_assistant_config("doctor")
        config3 = get_assistant_config("Doctor")
        
        assert config1 == config2 == config3
    
    def test_get_assistant_config_invalid(self):
        """Test getting invalid assistant configuration"""
        with pytest.raises(ValueError, match="Unsupported assistant type"):
            get_assistant_config("invalid_assistant")
        
        with pytest.raises(ValueError, match="Assistant type cannot be empty"):
            get_assistant_config("")
        
        with pytest.raises(ValueError, match="Assistant type must be a string"):
            get_assistant_config(None)
    
    def test_validate_assistant_config_valid(self):
        """Test validating valid assistant configuration"""
        valid_config = {
            "name": "Test Assistant",
            "system_prompt": "This is a test system prompt that is long enough to pass validation.",
            "temperature": 0.7
        }
        
        # Should not raise any exception
        validate_assistant_config(valid_config)
    
    def test_validate_assistant_config_missing_fields(self):
        """Test validating configuration with missing fields"""
        incomplete_config = {
            "name": "Test Assistant",
            "system_prompt": "Test prompt"
            # Missing temperature
        }
        
        with pytest.raises(ValueError, match="Missing required field: temperature"):
            validate_assistant_config(incomplete_config)
    
    def test_validate_assistant_config_invalid_name(self):
        """Test validating configuration with invalid name"""
        invalid_config = {
            "name": "",  # Empty name
            "system_prompt": "This is a test system prompt that is long enough to pass validation.",
            "temperature": 0.7
        }
        
        with pytest.raises(ValueError, match="Name must be a non-empty string"):
            validate_assistant_config(invalid_config)
    
    def test_validate_assistant_config_invalid_prompt(self):
        """Test validating configuration with invalid system prompt"""
        invalid_config = {
            "name": "Test Assistant",
            "system_prompt": "Short",  # Too short
            "temperature": 0.7
        }
        
        with pytest.raises(ValueError, match="System prompt must be at least"):
            validate_assistant_config(invalid_config)
    
    def test_validate_assistant_config_invalid_temperature(self):
        """Test validating configuration with invalid temperature"""
        invalid_config = {
            "name": "Test Assistant",
            "system_prompt": "This is a test system prompt that is long enough to pass validation.",
            "temperature": 3.0  # Too high
        }
        
        with pytest.raises(ValueError, match="Temperature must be between"):
            validate_assistant_config(invalid_config)
    
    def test_register_assistant_type_success(self):
        """Test successfully registering a new assistant type"""
        test_type = "test_assistant"
        test_name = "Test Assistant"
        test_prompt = "This is a test system prompt that is long enough for validation."
        
        # Clean up if it exists
        if test_type in ASSISTANT_CONFIGS:
            del ASSISTANT_CONFIGS[test_type]
        
        register_assistant_type(test_type, test_name, test_prompt, 0.5)
        
        # Verify it was registered
        assert test_type in ASSISTANT_CONFIGS
        config = get_assistant_config(test_type)
        assert config["name"] == test_name
        assert config["system_prompt"] == test_prompt
        assert config["temperature"] == 0.5
        
        # Clean up
        del ASSISTANT_CONFIGS[test_type]
    
    def test_register_assistant_type_duplicate(self):
        """Test registering duplicate assistant type"""
        with pytest.raises(ValueError, match="already exists"):
            register_assistant_type(ASSISTANT_TYPE_DOCTOR, "Duplicate", "Test prompt", 0.7)
    
    def test_register_assistant_type_invalid(self):
        """Test registering assistant type with invalid data"""
        with pytest.raises(ValueError, match="Assistant type must be a non-empty string"):
            register_assistant_type("", "Test", "Test prompt", 0.7)
    
    def test_get_available_assistant_types(self):
        """Test getting list of available assistant types"""
        types = get_available_assistant_types()
        
        assert isinstance(types, list)
        assert len(types) > 0
        assert ASSISTANT_TYPE_DOCTOR in types
        assert ASSISTANT_TYPE_LEGAL in types
        assert ASSISTANT_TYPE_GENERAL in types
    
    def test_get_config_summary(self):
        """Test getting configuration summary"""
        summary = get_config_summary()
        
        assert "total_assistants" in summary
        assert "assistant_types" in summary
        assert "assistants" in summary
        
        assert summary["total_assistants"] == len(ASSISTANT_CONFIGS)
        assert isinstance(summary["assistant_types"], list)
        assert isinstance(summary["assistants"], dict)
        
        # Check that each assistant has the expected fields in summary
        for assistant_type in summary["assistant_types"]:
            assistant_info = summary["assistants"][assistant_type]
            assert "name" in assistant_info
            assert "temperature" in assistant_info
            assert "prompt_length" in assistant_info
    
    def test_assistant_configs_are_valid(self):
        """Test that all built-in assistant configurations are valid"""
        for assistant_type, config in ASSISTANT_CONFIGS.items():
            # Should not raise any exception
            validate_assistant_config(config)
            
            # Additional checks
            assert isinstance(config["name"], str)
            assert len(config["name"]) > 0
            assert isinstance(config["system_prompt"], str)
            assert len(config["system_prompt"]) >= 50  # MIN_PROMPT_LENGTH
            assert isinstance(config["temperature"], (int, float))
            assert 0.0 <= config["temperature"] <= 2.0
    
    def test_config_immutability(self):
        """Test that returned configurations are copies and don't affect the original"""
        original_config = ASSISTANT_CONFIGS[ASSISTANT_TYPE_DOCTOR].copy()
        
        # Get config and modify it
        config = get_assistant_config(ASSISTANT_TYPE_DOCTOR)
        config["temperature"] = 999
        config["name"] = "Modified"
        
        # Original should be unchanged
        current_config = ASSISTANT_CONFIGS[ASSISTANT_TYPE_DOCTOR]
        assert current_config == original_config
        assert current_config["temperature"] != 999
        assert current_config["name"] != "Modified"

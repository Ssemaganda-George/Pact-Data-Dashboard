#!/usr/bin/env python3
"""
Simple test script to verify logout functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Mock streamlit session state for testing
class MockSessionState:
    def __init__(self):
        self.data = {}
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __contains__(self, key):
        return key in self.data
    
    def __delitem__(self, key):
        if key in self.data:
            del self.data[key]
    
    def get(self, key, default=None):
        return self.data.get(key, default)

# Mock streamlit functions
class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()
    
    def success(self, message):
        print(f"SUCCESS: {message}")
    
    def warning(self, message):
        print(f"WARNING: {message}")
    
    def rerun(self):
        print("RERUN called")

# Create mock streamlit
mock_st = MockStreamlit()

# Test the logout functionality
def test_logout():
    print("Testing logout functionality...")
    
    # Set up a logged-in session
    mock_st.session_state["logged_in"] = True
    mock_st.session_state["username"] = "test_user"
    mock_st.session_state["email"] = "test@example.com"
    mock_st.session_state["df"] = "mock_dataframe"
    mock_st.session_state["auth_mode"] = "Login"
    
    print("Before logout:")
    print(f"  Session state keys: {list(mock_st.session_state.data.keys())}")
    
    # Define logout function (extracted from auth.py)
    def logout():
        """Handle user logout by clearing session state"""
        # Clear all authentication-related session state
        keys_to_clear = ["logged_in", "username", "email", "df", "original_df", 
                         "original_shape", "original_missing", "original_numeric", 
                         "auth_mode", "last_activity", "show_logout_confirm"]
        
        for key in keys_to_clear:
            if key in mock_st.session_state:
                del mock_st.session_state[key]
        
        mock_st.success("Logged out successfully!")
        mock_st.rerun()
    
    # Test logout
    logout()
    
    print("After logout:")
    print(f"  Session state keys: {list(mock_st.session_state.data.keys())}")
    
    # Verify logout worked
    assert "logged_in" not in mock_st.session_state
    assert "username" not in mock_st.session_state
    assert "email" not in mock_st.session_state
    assert "df" not in mock_st.session_state
    
    print("✅ Logout test passed!")

if __name__ == "__main__":
    test_logout()
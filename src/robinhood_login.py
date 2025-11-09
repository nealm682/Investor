"""
Robinhood Login Module
Handles authentication to Robinhood using credentials from environment variables.
"""
import os
import robin_stocks.robinhood as r
import streamlit as st


def login_to_robinhood():
    """
    Logs into Robinhood using credentials from environment variables.
    
    Returns:
        bool: True if login successful, False otherwise
    """
    # Get credentials from environment variables
    username = os.getenv("ROBINHOOD_USERNAME")
    password = os.getenv("ROBINHOOD_PASSWORD")
    
    if not username or not password:
        st.warning("⚠️ Robinhood credentials not found in environment variables.")
        st.info("Please enter your credentials in the sidebar and click 'Save Credentials'")
        return False
    
    st.write(f"Attempting login for user: {username[:3]}***")
    
    try:
        # Attempt login - this will raise an exception if login fails
        login_result = r.login(
            username=username,
            password=password,
            expiresIn=86400,  # 24 hours
            by_sms=True  # Enable SMS-based MFA if needed
        )
        
        # If we get here, login was successful
        st.success("✅ Login successful!")
        return True
        
    except KeyError as ke:
        # This is the bug in robin_stocks - it tries to access data['detail'] but it doesn't exist
        st.error("❌ Login failed - Invalid credentials or authentication error")
        st.info("**Troubleshooting steps:**")
        st.write("1. Double-check your username (email) and password")
        st.write("2. Make sure your Robinhood account is active")
        st.write("3. Try logging into the Robinhood app/website to verify credentials")
        st.write("4. If you have 2FA enabled, you may need to handle it differently")
        st.warning(f"Technical detail: robin_stocks library error - {ke}")
        return False
        
    except Exception as e:
        error_msg = str(e)
        st.error(f"❌ Error during Robinhood login: {error_msg}")
        
        # Try to parse common error messages
        if "username" in error_msg.lower() or "password" in error_msg.lower():
            st.info("**Issue**: Invalid username or password")
            st.write("- Verify your email and password are correct")
            st.write("- Try logging into Robinhood's website to confirm")
        elif "mfa" in error_msg.lower() or "challenge" in error_msg.lower():
            st.info("**Issue**: Multi-Factor Authentication (MFA) required")
            st.write("- This app doesn't fully support interactive MFA yet")
            st.write("- Try disabling 2FA temporarily or use a different method")
        elif "locked" in error_msg.lower() or "restricted" in error_msg.lower():
            st.info("**Issue**: Account may be locked or restricted")
            st.write("- Check your Robinhood account status")
            st.write("- Contact Robinhood support if needed")
        else:
            st.info("**Common issues:**")
            st.write("- Incorrect username or password")
            st.write("- MFA (Multi-Factor Authentication) required")
            st.write("- Account locked or restricted")
            st.write("- Network connectivity issues")
        
        return False


def logout_from_robinhood():
    """
    Logs out from Robinhood.
    """
    try:
        r.logout()
        return True
    except Exception as e:
        st.error(f"Error during logout: {str(e)}")
        return False

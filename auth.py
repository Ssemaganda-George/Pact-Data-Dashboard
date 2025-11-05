import streamlit as st
from supabase import create_client
from config import IS_LOCAL, LOCAL_URL, LOCAL_KEY, REMOTE_URL, REMOTE_KEY

# Supabase setup
if IS_LOCAL:
    url = LOCAL_URL
    key = LOCAL_KEY
else:
    url = REMOTE_URL
    key = REMOTE_KEY

supabase = create_client(url, key)

def auth():
    st.title("PACT EDA Dashboard Authentication")
    
    # Buttons for mode selection
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", key="login_mode"):
            st.session_state["auth_mode"] = "Login"
    with col2:
        if st.button("Signup", key="signup_mode"):
            st.session_state["auth_mode"] = "Signup"
    
    auth_mode = st.session_state.get("auth_mode", "Login")
    
    if auth_mode == "Signup":
        st.subheader("Signup")
        new_username = st.text_input("Username")
        new_email = st.text_input("Email")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        if st.button("Signup", key="signup_submit"):
            if new_username and new_email and new_password:
                try:
                    # Check if email exists
                    result = supabase.table('users').select('*').eq('email', new_email).execute()
                    if result.data:
                        st.error("Email already exists.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        supabase.table('users').insert({'username': new_username, 'email': new_email, 'password': new_password}).execute()
                        st.success("Signup successful! Please login.")
                except Exception as e:
                    st.error(f"Connection error: {e}. Please check your Supabase setup.")
            else:
                st.error("Please fill all fields.")
    
    elif auth_mode == "Login":
        st.subheader("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login", key="login_submit"):
            try:
                result = supabase.table('users').select('*').eq('email', email).eq('password', password).execute()
                if result.data:
                    user = result.data[0]
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user['username']
                    st.session_state["email"] = user['email']
                    st.session_state["df"] = None
                    st.session_state["original_df"] = None
                    st.session_state["original_shape"] = None
                    st.session_state["original_missing"] = None
                    st.session_state["original_numeric"] = None
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
            except Exception as e:
                st.error(f"Connection error: {e}. Please check your Supabase setup.")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    auth()
    st.stop()
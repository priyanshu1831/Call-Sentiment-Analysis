# frontend/auth/auth_pages.py

import streamlit as st
import re
from .database import Database

def init_session_state():
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None

def show_login_page():
    st.title("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
                return False
            
            db = Database()
            user_id = db.verify_user(username, password)
            
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.success("Login successful!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
                return False

def show_register_page():
    st.title("Register")
    
    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")
        
        if submit:
            if not all([username, email, password, confirm_password]):
                st.error("Please fill in all fields")
                return False
            
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                st.error("Please enter a valid email address")
                return False
            
            if len(password) < 8:
                st.error("Password must be at least 8 characters long")
                return False
            
            if password != confirm_password:
                st.error("Passwords do not match")
                return False
            
            db = Database()
            if db.add_user(username, email, password):
                st.success("Registration successful! Please login.")
                return True
            else:
                st.error("Username already exists")
                return False
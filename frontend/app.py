# app.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import requests
import json
import re
import os
import sqlite3
from datetime import datetime
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Dict, List
import time

# Color scheme
COLORS = {
    'primary': '#2C3E50',
    'accent': '#E74C3C',
    'positive': '#2ECC71',
    'negative': '#E74C3C',
    'neutral': '#95A5A6'
}

# Database Management
class Database:
    def __init__(self, db_file="data/users.db"):
        self.db_file = db_file
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    filename TEXT,
                    analysis_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            conn.commit()

    def add_user(self, username, email, password):
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, generate_password_hash(password))
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def verify_user(self, username, password):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password_hash FROM users WHERE username = ?", 
                (username,)
            )
            result = cursor.fetchone()
            if result and check_password_hash(result[1], password):
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now(), result[0])
                )
                conn.commit()
                return result[0]
        return None

    def get_user_by_email(self, email):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            return cursor.fetchone()

# File Storage Management
class FileStorage:
    def __init__(self, base_dir="data/user_data"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def get_user_directory(self, user_id):
        user_dir = os.path.join(self.base_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def save_transcript(self, user_id, file_obj, filename):
        user_dir = self.get_user_directory(user_id)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{os.path.basename(filename)}"
        file_path = os.path.join(user_dir, safe_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_obj.getvalue())
        
        return safe_filename

    def save_analysis(self, user_id, filename, analysis_data):
        user_dir = self.get_user_directory(user_id)
        analysis_dir = os.path.join(user_dir, 'analysis')
        os.makedirs(analysis_dir, exist_ok=True)
        
        analysis_file = os.path.join(
            analysis_dir,
            f"{os.path.splitext(filename)[0]}_analysis.json"
        )
        
        with open(analysis_file, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        return analysis_file

    def get_user_files(self, user_id):
        user_dir = self.get_user_directory(user_id)
        files = []
        
        for file in os.listdir(user_dir):
            if os.path.isfile(os.path.join(user_dir, file)):
                files.append({
                    'type': 'transcript',
                    'filename': file,
                    'created': datetime.fromtimestamp(
                        os.path.getctime(os.path.join(user_dir, file))
                    ).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        analysis_dir = os.path.join(user_dir, 'analysis')
        if os.path.exists(analysis_dir):
            for file in os.listdir(analysis_dir):
                if file.endswith('_analysis.json'):
                    files.append({
                        'type': 'analysis',
                        'filename': file,
                        'created': datetime.fromtimestamp(
                            os.path.getctime(os.path.join(analysis_dir, file))
                        ).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        return sorted(files, key=lambda x: x['created'], reverse=True)

# Session Management
def init_session_state():
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None

def show_login_page():
    with st.form("login_form"):
        st.subheader("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns([1, 3])
        with col1:
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
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username or password")
                return False

def show_register_page():
    with st.form("register_form"):
        st.subheader("📝 Register")
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
        
        with col2:
            email = st.text_input("Email")
            confirm_password = st.text_input("Confirm Password", type="password")
        
        col1, col2 = st.columns([1, 3])
        with col1:
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
            if db.get_user_by_email(email):
                st.error("Email already registered")
                return False
            
            if db.add_user(username, email, password):
                st.success("Registration successful! Please login.")
                time.sleep(1)
                return True
            else:
                st.error("Username already exists")
                return False

def process_api_response(response_data):
    """Process and normalize API response data."""
    # Map mood to sentiment for consistency
    if 'overall_mood' in response_data:
        response_data['overall_sentiment'] = response_data.pop('overall_mood')
    
    if 'timeline' in response_data:
        for entry in response_data['timeline']:
            if 'mood' in entry:
                entry['sentiment'] = entry.pop('mood')
            
            # Ensure timestamp mapping
            if 'when' in entry:
                entry['timestamp'] = entry.pop('when')
            if 'who' in entry:
                entry['speaker'] = entry.pop('who')
    
    # Ensure speaker analysis mood mapping
    if 'speaker_analysis' in response_data:
        for speaker_data in response_data['speaker_analysis'].values():
            if 'avg_mood' in speaker_data:
                speaker_data['avg_sentiment'] = speaker_data.pop('avg_mood')
    
    return response_data

def parse_transcript(text: str) -> List[Dict]:
    lines = text.split('\n')
    transcript = []
    current_speaker = None
    current_text = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        speaker_match = re.match(r'\[(.*?)\s+(\d{2}:\d{2})\]', line)
        if speaker_match:
            if current_speaker and current_text:
                transcript.append({
                    'speaker': current_speaker,
                    'timestamp': timestamp,
                    'text': ' '.join(current_text)
                })
            
            speaker, timestamp = speaker_match.groups()
            current_speaker = speaker.strip()
            timestamp = f"[{timestamp}]"
            current_text = [line[speaker_match.end():].strip()]
        elif current_speaker:
            current_text.append(line)
    
    if current_speaker and current_text:
        transcript.append({
            'speaker': current_speaker,
            'timestamp': timestamp,
            'text': ' '.join(current_text)
        })
    
    return transcript

def show_sentiment_timeline(timeline_data):
    df = pd.DataFrame([
        {
            'time': t.get('timestamp', t.get('when', 'Unknown')),
            'speaker': t.get('speaker', t.get('who', 'Unknown')),
            'sentiment': t.get('sentiment', t.get('mood', {})).get('score', 0.0),
            'confidence': t.get('sentiment', t.get('mood', {})).get('confidence', 0.0),
            'emotion': t.get('sentiment', t.get('mood', {})).get('emotion', 'neutral'),
            'text': t.get('text', '')[:100]
        }
        for t in timeline_data
    ])
    
    fig = go.Figure()
    colors = {
        'Customer': COLORS['accent'],
        'Sales Agent': COLORS['primary']
    }
    
    # Calculate rolling averages for smoother lines
    window_size = 3
    for speaker in df['speaker'].unique():
        speaker_data = df[df['speaker'] == speaker].copy()
        speaker_data['smooth_sentiment'] = speaker_data['sentiment'].rolling(
            window=window_size, center=True, min_periods=1
        ).mean()
        
        fig.add_trace(go.Scatter(
            x=speaker_data['time'],
            y=speaker_data['smooth_sentiment'],
            name=speaker,
            mode='lines+markers',
            line=dict(
                color=colors.get(speaker, COLORS['neutral']),
                shape='spline',
                smoothing=0.3
            ),
            marker=dict(size=8),
            hovertemplate=(
                "<b>%{x}</b><br>" +
                "Sentiment: %{y:.2f}<br>" +
                "Confidence: %{customdata[0]:.2f}<br>" +
                "Emotion: %{customdata[1]}<br>" +
                "Text: %{customdata[2]}<extra></extra>"
            ),
            customdata=speaker_data[['confidence', 'emotion', 'text']].values
        ))
    
    fig.update_layout(
        title={
            'text': "Conversation Sentiment Timeline",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="Time",
        yaxis_title="Sentiment Score",
        yaxis=dict(
            range=[-1, 1],
            ticktext=['Very Negative', 'Negative', 'Neutral', 'Positive', 'Very Positive'],
            tickvals=[-1, -0.5, 0, 0.5, 1],
            gridcolor='lightgray'
        ),
        plot_bgcolor='white',
        hovermode='x unified'
    )
    
    return fig

def show_topic_analysis(results):
    """Display topic analysis with improved visualization."""
    st.markdown("### Topic Distribution")
    topic_data = pd.DataFrame({
        'Topic': [k.title() for k in results['topics'].keys()],
        'Coverage': list(results['topics'].values())
    }).sort_values('Coverage', ascending=False)
    
    if not topic_data.empty:
        fig = px.bar(
            topic_data,
            x='Topic',
            y='Coverage',
            color='Coverage',
            color_continuous_scale=[COLORS['neutral'], COLORS['primary']],
            text=topic_data['Coverage'].apply(lambda x: f"{x:.0%}")
        )
        
        fig.update_layout(
            showlegend=False,
            yaxis_tickformat='.0%'
        )
        
        st.plotly_chart(fig, use_container_width=True)

def show_speaker_analysis(speaker_data):
    """Display detailed speaker analysis."""
    for speaker, data in speaker_data.items():
        with st.expander(f"👤 {speaker}"):
            col1, col2 = st.columns(2)
            
            with col1:
                sentiment_score = data.get('avg_sentiment', data.get('avg_mood', 0.0))
                sentiment_icon = (
                    "🟢" if sentiment_score > 0.2 else
                    "🔴" if sentiment_score < -0.2 else
                    "🟡"
                )
                st.metric(
                    f"{sentiment_icon} Average Sentiment",
                    f"{sentiment_score:.2f}",
                    help="Range: -1 (negative) to +1 (positive)"
                )
                st.metric(
                    "Messages",
                    str(len(data.get('messages', []))),
                    help="Number of utterances"
                )
            
            with col2:
                if 'emotions' in data:
                    st.markdown("##### Emotion Distribution")
                    emotion_counts = {}
                    for emotion in data['emotions']:
                        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                    
                    total = len(data['emotions'])
                    for emotion, count in sorted(
                        emotion_counts.items(),
                        key=lambda x: x[1],
                        reverse=True
                    ):
                        if emotion != 'neutral':  # Show non-neutral emotions first
                            percentage = (count / total) * 100
                            st.progress(
                                percentage / 100,
                                text=f"{emotion.title()}: {percentage:.0f}%"
                            )

def show_user_history():
    """Display user's analysis history."""
    storage = FileStorage()
    files = storage.get_user_files(st.session_state.user_id)
    
    st.sidebar.markdown("### Recent Analyses")
    
    if not files:
        st.sidebar.info("No analysis history")
        return
    
    for file in files[:5]:  # Show last 5 files
        with st.sidebar.expander(f"{file['filename']} ({file['created']})"):
            if file['type'] == 'analysis':
                if st.button("View", key=file['filename']):
                    analysis_path = os.path.join(
                        storage.get_user_directory(st.session_state.user_id),
                        'analysis',
                        file['filename']
                    )
                    with open(analysis_path) as f:
                        analysis_data = json.load(f)
                        show_analysis_results(analysis_data)

def show_analysis_results(results):
    """Display complete analysis results."""
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sentiment_score = results.get('overall_sentiment', results.get('overall_mood', {})).get('score', 0.0)
        sentiment_icon = (
            "🟢" if sentiment_score > 0.2 else
            "🔴" if sentiment_score < -0.2 else
            "🟡"
        )
        st.metric(
            f"{sentiment_icon} Overall Sentiment",
            f"{sentiment_score:.2f}"
        )
    
    with col2:
        topics = results.get('topics', {})
        if topics:
            top_topic = max(topics.items(), key=lambda x: x[1])
            st.metric(
                "📌 Main Topic",
                top_topic[0].title(),
                f"{top_topic[1]:.0%} coverage"
            )
        else:
            st.metric("📌 Topics", "No topics detected")
    
    with col3:
        timeline = results.get('timeline', [])
        st.metric(
            "💬 Messages",
            str(len(timeline))
        )
    
    # Create analysis tabs
    tab1, tab2, tab3 = st.tabs([
        "📈 Sentiment Analysis",
        "🎯 Topics",
        "👥 Speaker Analysis"
    ])
    
    with tab1:
        if timeline:
            st.plotly_chart(
                show_sentiment_timeline(timeline),
                use_container_width=True
            )
        
        # Show key phrases
        st.markdown("### 🔑 Key Phrases")
        all_phrases = set()
        for entry in timeline:
            sentiment_data = entry.get('sentiment', entry.get('mood', {}))
            if isinstance(sentiment_data, dict):
                all_phrases.update(sentiment_data.get('key_phrases', []))
        
        if all_phrases:
            st.markdown(", ".join(f"`{phrase}`" for phrase in all_phrases))
        else:
            st.info("No key phrases detected")
    
    with tab2:
        show_topic_analysis(results)
    
    with tab3:
        show_speaker_analysis(results.get('speaker_analysis', {}))

def main():
    # Initialize session state
    init_session_state()
    
    st.set_page_config(
        page_title="Call Analysis Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    # Custom styling
    st.markdown("""
        <style>
        .main { padding: 1rem }
        .stMetric {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .stProgress .st-bo {
            background-color: #2980B9;
        }
        .stProgress .st-bp {
            background-color: #f8f9fa;
        }
        div[data-testid="stToolbar"] {
            display: none;
        }
        footer {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.user_id:
        # Show auth pages
        st.title("Call Analysis System")
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            show_login_page()
        
        with tab2:
            show_register_page()
        
        # Show features section
        st.markdown("---")
        st.markdown("### 🌟 Features")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            #### 📊 Sentiment Analysis
            - Real-time sentiment tracking
            - Emotion detection
            - Speaker-specific insights
            """)
        
        with col2:
            st.markdown("""
            #### 🎯 Topic Analysis
            - Automatic topic detection
            - Key phrase extraction
            - Topic evolution tracking
            """)
        
        with col3:
            st.markdown("""
            #### 📈 Visual Reports
            - Interactive charts
            - Downloadable reports
            - Historical analysis
            """)
    else:
        # Show main application
        st.sidebar.markdown(f"Welcome, {st.session_state.username}! 👋")
        
        # Logout button
        if st.sidebar.button("Logout 🚪"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
        
        # Show user's analysis history
        show_user_history()
        
        # Main content
        st.title("Call Transcript Analysis")
        st.markdown("""
        Analyze customer call transcripts for sentiment, topics, and insights.
        Upload your transcript file to begin.
        """)
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload transcript",
            type=['txt', 'json'],
            help="Supported formats: Raw text or JSON"
        )
        
        if uploaded_file:
            try:
                # Save file
                storage = FileStorage()
                filename = storage.save_transcript(
                    st.session_state.user_id,
                    uploaded_file,
                    uploaded_file.name
                )
                
                # Parse transcript
                if uploaded_file.type == "text/plain":
                    text = uploaded_file.read().decode()
                    transcript = parse_transcript(text)
                else:
                    transcript = json.load(uploaded_file)
                
                if not transcript:
                    st.error("No valid transcript content found!")
                    st.stop()
                
                # Analyze transcript
                with st.spinner("🔍 Analyzing transcript..."):
                    try:
                        response = requests.post(
                            'http://localhost:5000/analyze',
                            json={'transcript': transcript},
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            results = process_api_response(response.json())
                            
                            # Save analysis results
                            storage.save_analysis(
                                st.session_state.user_id,
                                filename,
                                results
                            )
                            
                            # Show results
                            show_analysis_results(results)
                        else:
                            st.error(f"Analysis failed: {response.text}")
                    
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error connecting to analysis service: {str(e)}")
                        st.info("Please make sure the backend server is running.")
                        st.stop()
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                with st.expander("Debug Details"):
                    st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
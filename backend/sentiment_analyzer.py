import spacy
from transformers import pipeline
import re
from typing import Dict, List, Optional
import logging
from datetime import datetime
import numpy as np
from collections import defaultdict

logging.basicConfig(
    format='%(asctime)s [%(levelname)s]: %(message)s',
    level=logging.INFO
)

class ConversationAnalyzer:
    def __init__(self, debug_mode: bool = False):
        self._debug = debug_mode
        self._setup_time = datetime.now()
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logging.warning("Downloading spaCy model - first time setup...")
            import os
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
        self.mood_detector = pipeline(
            "sentiment-analysis",
            model="nlptown/bert-base-multilingual-uncased-sentiment",
            device='cpu'
        )
        self.emotion_finder = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base"
        )
        self._topic_markers = {
            'pricing': [
                'price', 'cost', 'fee', 'discount', 'expensive', 'cheap'
            ],
            'product': [
                'feature', 'product', 'service', 'quality', 'work'
            ],
            'support': [
                'help', 'support', 'assist', 'guide', 'resolve'
            ],
            'technical': [
                'error', 'issue', 'problem', 'bug', 'fix'
            ],
            'satisfaction': [
                'happy', 'satisfied', 'great', 'amazing', 'good'
            ]
        }
        
        if self._debug:
            logging.info(f"Analyzer initialized in {(datetime.now() - self._setup_time).total_seconds():.2f}s")
    
    def clean_chat(self, text: str) -> str:
        text = re.sub(r'\[.*?\]', '', text)
        text = text.replace('…', '...').replace('️', '')
        text = ' '.join(text.split())
        
        return text.strip()
    
    def get_speaker_mood(self, text: str) -> Dict:
        if not text.strip():
            return self._get_neutral_mood()
            
        try:
            base_result = self.mood_detector(text)
            if not base_result:
                return self._get_neutral_mood()
                
            result = base_result[0]
            mood_score = (float(result['label'].split()[0]) - 3) / 2
            emotion = self.emotion_finder(text)[0]
            doc = self.nlp(text)
            key_bits = []
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) > 1 and not chunk.text.lower().startswith(('the', 'a', 'an')):
                    key_bits.append(chunk.text)
            
            return {
                'score': round(mood_score, 2),
                'confidence': round(result['score'], 2),
                'emotion': emotion['label'],
                'key_phrases': key_bits[:3]
            }
            
        except Exception as e:
            logging.error(f"Mood analysis failed: {str(e)}")
            return self._get_neutral_mood()
    
    def _get_neutral_mood(self) -> Dict:
        return {
            'score': 0.0,
            'confidence': 0.0,
            'emotion': 'neutral',
            'key_phrases': []
        }
    
    def find_topics(self, text: str) -> Dict[str, float]:
        text = text.lower()
        scores = defaultdict(float)
        for topic, keywords in self._topic_markers.items():
            matches = sum(1 for kw in keywords if kw in text)
            if matches:
                scores[topic] = matches / len(keywords)
        if scores:
            total = sum(scores.values())
            scores = {k: round(v/total, 2) for k, v in scores.items()}
        
        return dict(scores)
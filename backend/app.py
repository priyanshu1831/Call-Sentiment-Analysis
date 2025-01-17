from collections import defaultdict
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from sentiment_analyzer import ConversationAnalyzer
import logging
import time

app = Flask(__name__)
analyzer = ConversationAnalyzer(debug_mode=True)
CORS(app)

ALLOWED_ORIGINS = [
    'https://call-sentiment-analysis-production.up.railway.app',
    'http://call-sentiment-analysis.railway.internal:8080',
    'http://localhost:8501'
]   

@app.route('/analyze', methods=['POST'])
def analyze_conversation():
    start_time = time.time()
    try:
        data = request.get_json()
        if not data or 'transcript' not in data:
            return jsonify({
                'error': 'Missing transcript data',
                'example_format': {
                    'transcript': [
                        {'speaker': 'Agent', 'text': 'Hello', 'timestamp': '[00:00]'}
                    ]
                }
            }), 400
        results = {
            'overall_mood': {'score': 0.0, 'confidence': 0.0},
            'speaker_analysis': {},
            'topics': defaultdict(float),
            'timeline': []
        }
        all_moods = []
        for entry in data['transcript']:
            if not entry.get('text', '').strip():
                continue
            text = analyzer.clean_chat(entry['text'])
            speaker = entry.get('speaker', 'Unknown')
            timestamp = entry.get('timestamp', '')
            mood_data = analyzer.get_speaker_mood(text)
            topic_data = analyzer.find_topics(text)
            if speaker not in results['speaker_analysis']:
                results['speaker_analysis'][speaker] = {
                    'messages': [],
                    'avg_mood': 0.0,
                    'emotions': []
                }
            results['speaker_analysis'][speaker]['messages'].append(mood_data)
            results['speaker_analysis'][speaker]['emotions'].append(mood_data['emotion'])
            results['timeline'].append({
                'when': timestamp,
                'who': speaker,
                'mood': mood_data,
                'topics': topic_data
            })
            for topic, score in topic_data.items():
                results['topics'][topic] += score
            all_moods.append(mood_data)
        if all_moods:
            results['overall_mood'] = {
                'score': round(np.mean([m['score'] for m in all_moods]), 2),
                'confidence': round(np.mean([m['confidence'] for m in all_moods]), 2)
            }
        topic_total = sum(results['topics'].values())
        if topic_total:
            results['topics'] = {
                k: round(v/topic_total, 2) 
                for k, v in results['topics'].items()
            }
        for speaker_data in results['speaker_analysis'].values():
            if speaker_data['messages']:
                speaker_data['avg_mood'] = round(
                    np.mean([m['score'] for m in speaker_data['messages']]), 
                    2
                )
                emotion_counts = defaultdict(int)
                for emotion in speaker_data['emotions']:
                    emotion_counts[emotion] += 1
                speaker_data['top_emotions'] = sorted(
                    emotion_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:2]
        
        process_time = round(time.time() - start_time, 2)
        logging.info(f"Processed transcript in {process_time}s")
        
        return jsonify({
            **results,
            'meta': {
                'process_time': process_time,
                'utterance_count': len(data['transcript'])
            }
        })
        
    except Exception as e:
        logging.error(f"Analysis failed: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'failed'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
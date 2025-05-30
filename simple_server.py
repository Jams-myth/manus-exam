#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import json

app = Flask(__name__, 
            static_folder='build/static',
            template_folder='build')

# Load question data
def load_questions(subject):
    if subject == 'mathematics':
        file_path = 'exam_papers/N5_Mathematics_Paper1-Non-calculator_2022_questions.json'
    else:
        file_path = 'exam_papers/Applications_of_Mathematics_questions.json'
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading questions: {e}")
        return []

# Routes
@app.route('/')
def index():
    return send_from_directory('build', 'index.html')

@app.route('/practice')
def practice():
    return send_from_directory('build', 'practice.html')

@app.route('/practice/mathematics')
def practice_mathematics():
    questions = load_questions('mathematics')
    return render_template('practice_subject.html', 
                          subject='Mathematics',
                          questions=[{
                              'question_id': i,
                              'question_num': q['question_number'],
                              'text': q['text'],
                              'marks': q['marks'] if q['marks'] is not None else '?'
                          } for i, q in enumerate(questions)])

@app.route('/practice/applications')
def practice_applications():
    questions = load_questions('applications')
    return render_template('practice_subject.html', 
                          subject='Applications of Mathematics',
                          questions=[{
                              'question_id': i,
                              'question_num': q['question_number'],
                              'text': q['text'],
                              'marks': q['marks'] if q['marks'] is not None else '?'
                          } for i, q in enumerate(questions)])

@app.route('/question/<int:question_id>')
def question(question_id):
    subject = request.args.get('subject', 'mathematics')
    questions = load_questions(subject)
    
    if question_id < 0 or question_id >= len(questions):
        return "Question not found", 404
    
    q = questions[question_id]
    return render_template('question.html',
                          question={
                              'question_id': question_id,
                              'question_num': q['question_number'],
                              'text': q['text'],
                              'marks': q['marks'] if q['marks'] is not None else '?',
                              'subject': 'Mathematics' if subject == 'mathematics' else 'Applications of Mathematics',
                              'year': '2022',
                              'topic': q.get('metadata', {}).get('topic', '')
                          },
                          diagrams=[])

@app.route('/about')
def about():
    return send_from_directory('build', 'about.html')

@app.route('/upload')
def upload():
    return send_from_directory('build', 'upload.html')

@app.route('/admin')
def admin():
    return send_from_directory('build', 'admin.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('build/static', path)

@app.route('/api/questions/<subject>')
def api_questions(subject):
    if subject not in ['mathematics', 'applications']:
        return jsonify({"error": "Invalid subject"}), 400
    
    questions = load_questions(subject)
    return jsonify(questions)

@app.route('/api/submit_answer', methods=['POST'])
def submit_answer():
    # Mock answer submission endpoint
    return jsonify({
        "correct": True,
        "marks_awarded": 2,
        "total_marks": 2,
        "feedback": "Correct answer! Well done.",
        "detailed_feedback": [
            {
                "point": "Mathematical notation",
                "feedback": "Correct use of mathematical notation.",
                "marks_awarded": 1,
                "marks_available": 1
            },
            {
                "point": "Final answer",
                "feedback": "Correct final answer.",
                "marks_awarded": 1,
                "marks_available": 1
            }
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

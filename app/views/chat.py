from flask import Blueprint, jsonify, request, Response, stream_with_context
from flask_login import login_required, current_user
from app import db
from app.models.chat import Conversation, ChatMessage
from app.views.search import search, search_reviews
import json
import time
import openai
from flask import render_template

chat = Blueprint('chat', __name__)

@chat.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.updated_at.desc()).all()
    
    result = []
    for c in conversations:
        first_message = ChatMessage.query.filter_by(conversation_id=c.id, role='user').order_by(ChatMessage.created_at).first()
        result.append({
            'id': c.id, 
            'created_at': c.created_at,
            'first_query': first_message.content if first_message else None
        })
    
    return jsonify(result)

@chat.route('/conversations', methods=['POST'])
@login_required
def create_conversation():
    conversation = Conversation(user_id=current_user.id)
    db.session.add(conversation)
    db.session.commit()
    return jsonify({'id': conversation.id, 'created_at': conversation.created_at})

@chat.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(conversation)
    db.session.commit()
    return '', 204

@chat.route('/conversations/<int:conversation_id>/messages', methods=['GET'])
@login_required
def get_conversation_messages(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    messages = ChatMessage.query.filter_by(conversation_id=conversation_id).order_by(ChatMessage.created_at).all()
    return jsonify([{
        'id': m.id,
        'role': m.role,
        'content': m.content,
        'intent_analysis': m.intent_analysis,
        'search_results': m.search_results,
        'ai_response': m.ai_response,
        'timing_stats': m.timing_stats,
        'created_at': m.created_at
    } for m in messages])

@chat.route('/conversations/<int:conversation_id>/messages', methods=['POST'])
@login_required
def send_message(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    def generate():
        start_time = time.time()
        
        # Save user message
        user_chat_message = ChatMessage(conversation_id=conversation_id, role='user', content=user_message)
        db.session.add(user_chat_message)
        db.session.commit()
        # Analyze intent
        client = openai.OpenAI()
        intent_analysis_start = time.time()

        # Get conversation history
        conversation_history = ChatMessage.query.filter_by(conversation_id=conversation_id).order_by(ChatMessage.created_at).all()
        # Prepare messages for intent analysis
        messages = [
            {"role": "system", "content": 
             "Analyze the user's intent and return a JSON-formatted list of function calls. \n"
             "Available functions are: \n"
             "1. search_courses(course_name: str) - Use when the user is asking about a specific course or courses. If the keyword is a course name, use this function. \n"
             "2. search_reviews(query: str) - Use when the user is asking about reviews or opinions on courses. \n"
             "3. get_courses_by_teacher(teacher_name: str) - Use when the user is asking about courses taught by a specific teacher. \n"
             "If no function call is needed, return an empty list. \n"
             "Examples: \n"
             "1. User: 'What are the requirements for Calculus?' \n"
             "Assistant: [{\"function\": \"search_courses\", \"args\": {\"course_name\": \"Calculus\"}}] \n"
             "2. User: 'What are the reviews for the Data Structures course?' \n"
             "Assistant: [{\"function\": \"search_reviews\", \"args\": {\"query\": \"Data Structures\"}}] \n"
             "3. User: 'Who teaches the Computer Science courses?' \n"
             "Assistant: [{\"function\": \"get_courses_by_teacher\", \"args\": {\"teacher_name\": \"John Smith\"}}] \n"
             "4. User: 'What are the requirements for Calculus?' \n"
             "Assistant: [{\"function\": \"search_courses\", \"args\": {\"course_name\": \"Calculus\"}}] \n"
             "5. User: 'What are the reviews for the Data Structures course?' \n"
             "Assistant: [{\"function\": \"search_reviews\", \"args\": {\"query\": \"Data Structures\"}}] \n"
             "6. User: 'Who teaches the Computer Science courses?' \n"
             "Assistant: [{\"function\": \"get_courses_by_teacher\", \"args\": {\"teacher_name\": \"John Smith\"}}] \n"}
        ]
        # Add conversation history to messages
        for message in conversation_history:
            messages.append({"role": message.role, "content": message.content})
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        intent_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=150
        )
        intent_analysis = intent_response.choices[0].message.content
        intent_analysis_time = time.time() - intent_analysis_start
        # Extract only the JSON content from the intent analysis
        intent_analysis_json = intent_analysis.strip()
        if intent_analysis_json.startswith('```json'):
            intent_analysis_json = intent_analysis_json[7:]
        if intent_analysis_json.endswith('```'):
            intent_analysis_json = intent_analysis_json[:-3]
        intent_analysis_json = intent_analysis_json.strip()

        # Update the intent_analysis variable with the extracted JSON
        try:
            intent_data = json.loads(intent_analysis_json)
            yield f"data: {json.dumps({'type': 'intent_analysis', 'content': intent_data})}\n\n"
        except json.JSONDecodeError:
            print("Error parsing intent analysis JSON")
            intent_data = []

        # Parse intent and execute search
        search_start = time.time()
        search_results = []
        num_results = 10
        try:
            # Check if intent_data is a list, if not, convert it to a list
            if not isinstance(intent_data, list):
                intent_data = [intent_data]
            for func_call in intent_data:
                if isinstance(func_call, dict) and 'function' in func_call and 'args' in func_call:
                    if func_call['function'] == 'search_courses':
                        results = search([func_call['args']['course_name']], 1, num_results)
                        search_results.extend([{'type': 'course', 'data': {
                            'id': course.id,
                            'name_with_teachers_short': course.name_with_teachers_short,
                            'summary': course.summary
                        }} for course in results.items if course.summary])
                    elif func_call['function'] == 'search_reviews':
                        results = search_reviews([func_call['args']['query']], 1, num_results, current_user)
                        search_results.extend([{'type': 'review', 'data': {
                            'id': review.id,
                            'course_id': review.course_id,
                            'name_with_teachers_short': review.course.name_with_teachers_short,
                            'author': review.author.name,
                            'content': review.content
                        }} for review in results.items])
                    elif func_call['function'] == 'get_courses_by_teacher':
                        results = search([func_call['args']['teacher_name']], 1, num_results)
                        search_results.extend([{'type': 'course', 'data': {
                            'id': course.id,
                            'name_with_teachers_short': course.name_with_teachers_short,
                            'summary': course.summary
                        }} for course in results.items if course.summary])
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"Error processing intent data: {str(e)}")
            pass  # If intent analysis didn't return valid JSON, we'll just skip the search

        search_time = time.time() - search_start
        yield f"data: {json.dumps({'type': 'search_results', 'content': search_results})}\n\n"

        # Generate context from search results
        truncate_length = 1000
        context = ""
        for result in search_results:
            if result is None:
                continue
            if result.get('type') == 'course' and result.get('data'):
                course_data = result['data']
                summary = course_data.get('summary', '').strip()
                if summary:
                    context += f"Course: {course_data.get('name_with_teachers_short', 'Unknown')}\n=== BEGIN SUMMARY ===\n{summary[:truncate_length]}...\n=== END SUMMARY ===\n\n"
            elif result.get('type') == 'review' and result.get('data'):
                review_data = result['data']
                context += f"Review for {review_data.get('name_with_teachers_short', 'Unknown')} by {review_data.get('author', 'Unknown')}:\n=== BEGIN REVIEW ===\n{review_data.get('content', '')[:truncate_length]}...\n=== END REVIEW ===\n\n"

        # Query LLM with context and stream response
        ai_response_start = time.time()
        messages = [
            {"role": "system", "content": "You are a helpful assistant for a university course review system. Use the provided context to answer user queries."}
        ]
        
        # Add conversation history
        for message in conversation_history:
            messages.append({"role": message.role, "content": message.content})
        
        # Add context and current user query
        messages.append({"role": "user", "content": f"Context:\n=== BEGIN CONTEXT ===\n{context}\n=== END CONTEXT ===\n\nUser query: {user_message}"})
        
        ai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True
        )

        full_ai_response = ""
        for chunk in ai_response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_ai_response += content
                yield f"data: {json.dumps({'type': 'ai_response', 'content': content})}\n\n"

        ai_response_time = time.time() - ai_response_start
        total_time = time.time() - start_time

        # Save assistant message and timing stats
        timing_stats = {
            'intent_analysis_time': intent_analysis_time,
            'search_time': search_time,
            'ai_response_time': ai_response_time,
            'total_time': total_time
        }
        assistant_chat_message = ChatMessage(
            conversation_id=conversation_id,
            role='assistant',
            content=full_ai_response,
            intent_analysis=json.dumps(intent_data),
            search_results=json.dumps(search_results),
            ai_response=full_ai_response,
            timing_stats=json.dumps(timing_stats)
        )
        db.session.add(assistant_chat_message)
        db.session.commit()

        yield f"data: {json.dumps({'type': 'timing_stats', 'content': timing_stats})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), content_type='text/event-stream')

@chat.route('/')
def index():
    return render_template('chat.html')

from flask import Blueprint, request, jsonify, session, Response, stream_with_context
from flask_login import current_user
from app import app, db
from app.models.chat import ChatHistory, ChatMessage
from app.models.course import Course
from app.models.review import Review
from app.models.user import Teacher
from app.views.search import search_reviews, search as search_courses
from app.models.course import course_teachers
from flask import render_template
import json
import openai
import traceback
import time
from sqlalchemy import func
from sqlalchemy.orm import scoped_session, sessionmaker

chat = Blueprint('chat', __name__)

def get_chat_messages(user_query, context, chat_histories):
    messages = [
        {"role": "system", "content": "You are a helpful assistant for iCourse.club, a course review website for USTC students. Use the provided context to answer questions about courses and reviews. Answer questions elaborately. Include all relevant information in the context. If the provided context is not enough, tell the user that you don't know."},
    ]

    for message in chat_histories:
        messages.append({"role": message.role, "content": message.content})

    user_prompt = ""
    if context:
        user_prompt += f"Context for the query:\n=== BEGIN CONTEXT ===\n{context}\n=== END CONTEXT ===\n\n"
    user_prompt += f"User query: {user_query}"
    messages.append({"role": "user", "content": user_prompt})

    return messages

def call_openai(messages, json_response=False):
    try:
        client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])
        if json_response:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                response_format={ "type": "json_object" },
            )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
            )

        for chunk in response:
            if chunk.choices[0].finish_reason is not None:
                break
            yield chunk.choices[0].delta.content

    except Exception as e:
        print(f"Error in call_openai: {str(e)}")
        yield "I'm sorry, but I encountered an error while processing your request. Please try again later."

def analyze_intent(user_query):
    messages = [
        {"role": "system", "content": "You are an AI assistant that analyzes user queries and generates appropriate API calls in JSON format. The available API calls are:\n"
                                      "a) fetch_courses(course_name): Fetch a list of courses and review summary by course name. If the keyword looks like a course name, use this function.\n"
                                      "b) fetch_reviews(course_name=None, author=None): Fetch a list of reviews by course name or author.\n"
                                      "c) fetch_reviews_by_keyword(keyword): Fetch a list of reviews by keyword in review content\n"
                                      "d) fetch_courses_by_teacher(teacher_name): Fetch a list of courses by teacher name. If the keyword looks like a teacher name, use this function.\n"
                                      "If the query doesn't require additional context, return 'direct_response'.\n"
                                      "If the query involves multiple courses or teachers, return a list of API calls instead of a single one.\n"
                                      "Example output: [{\"function\": \"fetch_courses\", \"params\": {\"course_name\": \"Database\"}}]\n"},
        {"role": "user", "content": f"Analyze this query and generate appropriate API call(s) in JSON format: {user_query}"}
    ]

    response_gen = call_openai(messages)
    response = ""
    for token in response_gen:
        response += token
    print(response)
    
    try:
        # Remove headers and footers before parsing JSON
        cleaned_response = response.strip().lstrip('```json').rstrip('```')
        json_response = json.loads(cleaned_response)
        return json_response
    except json.JSONDecodeError:
        print(f"Invalid JSON response: {response}")
        return "direct_response"


def execute_api_calls(api_calls):
    results = []
    for call in api_calls:
        print(call)
        if call['function'] == 'fetch_courses':
            courses = search_courses(call['params']['course_name'].split(" "), 1, 10)
            results.extend([{
                'function': 'fetch_courses',
                'course_id': course.id,
                'course_name': course.name,
                'name_with_teachers_short': course.name_with_teachers_short,
                'summary': course.summary
            } for course in courses.items if course.summary])
        elif call['function'] == 'fetch_reviews':
            reviews = []
            if call['params'].get('course_name'):
                reviews = search_reviews(call['params']['course_name'].split(" "), 1, 10)
            elif call['params'].get('author'):
                reviews = search_reviews(call['params']['author'].split(" "), 1, 10)
            review_max_length = 1000
            results.extend([{
                'function': 'fetch_reviews',
                'id': review.id,
                'title': review.title,
                'content': review.content[:review_max_length] + '...' if len(review.content) > review_max_length else review.content,
                'rating': review.rating,
                'author': review.author,
                'course_name': review.course_name,
            } for review in reviews.items])
        elif call['function'] == 'fetch_reviews_by_keyword':
            keyword_reviews = search_reviews(call['params']['keyword'].split(" "), 1, 10, current_user)
            results.extend([{
                'function': 'fetch_reviews_by_keyword',
                'id': review.id,
                'title': review.title,
                'content': review.content[:review_max_length] + '...' if len(review.content) > review_max_length else review.content,
                'rating': review.rating,
                'author': review.author,
                'course_name': review.course_name,
            } for review in keyword_reviews.items])
        elif call['function'] == 'fetch_courses_by_teacher':
            courses = search_courses(call['params']['teacher_name'].split(" "), 1, 10)
            results.extend([{
                'function': 'fetch_courses_by_teacher',
                'id': course.id,
                'name': course.name,
                'name_with_teachers_short': course.name_with_teachers_short,
                'summary': course.summary
            } for course in courses.items if course.summary])
    return results

def generate_context(api_results):
    if isinstance(api_results, dict):
        api_results = [api_results]
    context = ""
    for result in api_results:
        function = result.get('function', '')
        if function == 'fetch_courses':
            context += f"Course: {result.get('course_name', 'N/A')}\n"
            context += f"Course ID: {result.get('course_id', 'N/A')}\n"
            context += f"Course with Teachers: {result.get('name_with_teachers_short', 'N/A')}\n"
            context += f"Course Summary: {result.get('summary', 'N/A')}\n"
        elif function in ['fetch_reviews', 'fetch_reviews_by_keyword']:
            context += f"Review ID: {result.get('id', 'N/A')}\n"
            context += f"Title: {result.get('title', 'N/A')}\n"
            context += f"Rating: {result.get('rating', 'N/A')}\n"
            context += f"Author: {result.get('author', 'N/A')}\n"
            context += f"Course: {result.get('course_name', 'N/A')}\n"
            context += f"=== Begin review content ===\n"
            context += f"{result.get('content', 'N/A')}\n"
            context += f"=== End review content ===\n"
        elif function == 'fetch_courses_by_teacher':
            context += f"Teacher: {result.get('name', 'N/A')}\n"
            context += f"Teacher ID: {result.get('id', 'N/A')}\n"
            context += f"Associated Course: {result.get('name_with_teachers_short', 'N/A')}\n"
            context += f"Course Summary: {result.get('summary', 'N/A')}\n"
        context += "\n"
    return context

@chat.route('/new_message', methods=['POST'])
def new_message():
    try:
        data = request.get_json()
        user_id = current_user.id if current_user.is_authenticated else None
        session_id = session.get('session_id') if user_id is None else None

        chat_history = ChatHistory.query.filter_by(id=data['conversation_id'], user_id=user_id, session_id=session_id).first()
        if not chat_history:
            return jsonify({'error': 'Conversation not found'}), 404

        chat_histories = ChatMessage.query.filter_by(chat_history_id=chat_history.id).order_by(ChatMessage.created_at).all()
        
        user_message = ChatMessage(chat_history_id=chat_history.id, role='user', content=data['message'])
        db.session.add(user_message)
        db.session.commit()

        def generate():
            start_time = time.time()
            
            # Analyze intent
            intent_analysis_start = time.time()
            intent_analysis = analyze_intent(data['message'])
            intent_analysis_time = time.time() - intent_analysis_start
            yield f"data: {json.dumps({'type': 'intent_analysis', 'content': intent_analysis, 'time': intent_analysis_time})}\n\n"

            if isinstance(intent_analysis, str) or intent_analysis[0]['function'] == "direct_response":
                chat_messages = get_chat_messages(data['message'], "", chat_histories)
                ai_response = ""
                first_token_time = None
                for token in call_openai(chat_messages):
                    if first_token_time is None:
                        first_token_time = time.time() - start_time
                    ai_response += token
                    yield f"data: {json.dumps({'type': 'ai_response', 'content': token})}\n\n"

                total_time = time.time() - start_time
                save_ai_response(chat_history.id, ai_response, 0, 0, first_token_time, total_time, "", [], intent_analysis_time)
                yield f"data: {json.dumps({'type': 'timing_info', 'intent_analysis_time': intent_analysis_time, 'search_time': 0, 'context_length': 0, 'time_to_first_token': first_token_time, 'total_time': total_time})}\n\n"
            else:
                # Execute API calls
                api_start_time = time.time()
                api_results = execute_api_calls(intent_analysis)
                api_time = time.time() - api_start_time
                yield f"data: {json.dumps({'type': 'api_results', 'content': api_results})}\n\n"

                # Generate context
                context = generate_context(api_results)
                context_length = len(context)

                # Generate AI response
                chat_messages = get_chat_messages(data['message'], context, chat_histories)
                ai_response = ""
                first_token_time = None
                for token in call_openai(chat_messages):
                    if first_token_time is None:
                        first_token_time = time.time() - start_time - api_time
                    ai_response += token
                    yield f"data: {json.dumps({'type': 'ai_response', 'content': token})}\n\n"

                total_time = time.time() - start_time
                save_ai_response(chat_history.id, intent_analysis, ai_response, api_time, context_length, first_token_time, total_time, context, api_results, intent_analysis_time)
                yield f"data: {json.dumps({'type': 'timing_info', 'intent_analysis_time': intent_analysis_time, 'search_time': api_time, 'context_length': context_length, 'time_to_first_token': first_token_time, 'total_time': total_time})}\n\n"

        return Response(stream_with_context(generate()), content_type='text/event-stream')

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


def save_ai_response(chat_history_id, intent_analysis, ai_response, api_time, context_length, time_to_first_token, total_time, context, api_results, intent_analysis_time):
    ai_message = ChatMessage(
        chat_history_id=chat_history_id,
        role='assistant',
        content=ai_response,
        intent_analysis=intent_analysis,
        search_time=api_time,
        context_length=context_length,
        time_to_first_token=time_to_first_token,
        total_response_time=total_time,
        context=context,
        search_results=json.dumps(api_results),
        intent_analysis_time=intent_analysis_time
    )
    db.session.add(ai_message)
    db.session.commit()

@chat.route('/chat_history/<int:conversation_id>', methods=['GET'])
def get_chat_history(conversation_id):
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None
    
    chat_history = ChatHistory.query.filter_by(user_id=user_id, session_id=session_id, id=conversation_id).first()
    if not chat_history:
        return jsonify([])
    
    messages = ChatMessage.query.filter_by(chat_history_id=chat_history.id).order_by(ChatMessage.created_at).all()
    result = [{
        'role': msg.role, 
        'content': msg.content,
        'intent_analysis_time': msg.intent_analysis_time,
        'search_time': msg.search_time,
        'time_to_first_token': msg.time_to_first_token,
        'total_response_time': msg.total_response_time,
        'context_length': msg.context_length,
        'search_results': msg.search_results,
        'intent_analysis': msg.intent_analysis,
    } for msg in messages]

    return jsonify(result)

@chat.route('/conversations', methods=['GET'])
def get_conversations():
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None

    conversations = ChatHistory.query.filter_by(user_id=user_id, session_id=session_id).order_by(ChatHistory.updated_at.desc()).all()
    
    result = []
    for conv in conversations:
        message_count = ChatMessage.query.filter_by(chat_history_id=conv.id).count()
        if message_count > 0 or conv == conversations[0]:
            result.append({
                'id': conv.id,
                'created_at': conv.created_at,
                'updated_at': conv.updated_at,
                'message_count': message_count,
                'first_query': conv.first_query,
            })
    
    return jsonify(result)

@chat.route('/new_conversation', methods=['POST'])
def create_conversation():
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None
    
    new_conversation = ChatHistory(user_id=user_id, session_id=session_id)
    db.session.add(new_conversation)
    db.session.commit()
    
    result = {
        'id': new_conversation.id,
        'created_at': new_conversation.created_at,
        'updated_at': new_conversation.updated_at
    }

    return jsonify(result), 201

@chat.route('/conversation/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None
    
    conversation = ChatHistory.query.filter_by(id=conversation_id).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    if conversation.user_id != user_id and conversation.session_id != session_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(conversation)
    db.session.commit()
    
    return '', 204

@chat.route('/', methods=['GET'])
def chat_index():
    return render_template('chat.html')

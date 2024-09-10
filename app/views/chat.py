from flask import Blueprint, request, jsonify, session, Response
from flask_login import current_user
from app import app
from app import db
from app.models.chat import ChatHistory, ChatMessage
from app.views.search import search_reviews
from flask import render_template
import json
import openai
import traceback
import time

chat = Blueprint('chat', __name__)


def get_chat_messages(user_query, context, chat_histories):
    messages = [
        {"role": "system", "content": "You are a helpful assistant for iCourse.club, a course review website for USTC students. Use the provided context to answer questions about courses and reviews."},
    ]

    # Add chat histories to the messages
    for message in chat_histories:
        messages.append({"role": message.role, "content": message.content})

    messages.append({"role": "user", "content": f"Context: {context}\n\nUser query: {user_query}"})

    return messages


def call_openai(messages):
    try:
        client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].finish_reason is not None:
                break
            yield chunk.choices[0].delta.content

    except Exception as e:
        print(f"Error in call_openai: {str(e)}")
        yield "I'm sorry, but I encountered an error while processing your request. Please try again later."


@chat.route('/new_conversation', methods=['POST'])
def new_conversation():
    # Get user ID or session ID
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None
    
    try:
        # Create a new chat history
        new_chat = ChatHistory(user_id=user_id, session_id=session_id)
        db.session.add(new_chat)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'New conversation created successfully',
            'conversation_id': new_chat.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to create new conversation: {str(e)}'
        }), 500


@chat.route('/new_message', methods=['POST'])
def new_message():
    try:
        data = validate_request()
        user_id, session_id = get_user_info()
        check_ongoing_chat()
        
        session['chat_in_progress'] = True
        
        chat_history = get_or_create_chat_history(user_id, session_id, data['conversation_id'])
        chat_histories = get_chat_histories(chat_history.id)
        
        is_first_query = len(chat_histories) == 0
        add_user_message(chat_history.id, data['message'])
        
        if is_first_query:
            save_first_query(chat_history, data['message'])
        
        search_results, search_time = perform_search(data['message'], current_user)
        
        context = generate_context(search_results)
        chat_messages = get_chat_messages(data['message'], context, chat_histories)
        
        return Response(generate_response(chat_history.id, chat_messages, search_results, search_time, context), content_type='text/event-stream')
    
    except Exception as e:
        return handle_error(e)
    
    finally:
        session['chat_in_progress'] = False


def validate_request():
    if not request.is_json:
        raise ValueError('Request must be JSON')
    
    data = request.get_json()
    if not data.get('message') or not data.get('conversation_id'):
        raise ValueError('Invalid request')
    
    return data


def get_user_info():
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None
    return user_id, session_id


def check_ongoing_chat():
    if session.get('chat_in_progress'):
        raise ValueError('A chat request is already in progress')


def get_or_create_chat_history(user_id, session_id, conversation_id):
    chat_history = ChatHistory.query.filter_by(user_id=user_id, session_id=session_id, id=conversation_id).first()
    if not chat_history:
        raise ValueError('Conversation not found')
    return chat_history


def get_chat_histories(chat_history_id):
    return ChatMessage.query.filter_by(chat_history_id=chat_history_id).order_by(ChatMessage.created_at).all()


def add_user_message(chat_history_id, user_query):
    user_message = ChatMessage(chat_history_id=chat_history_id, role='user', content=user_query)
    db.session.add(user_message)
    db.session.commit()
    return user_message


def save_first_query(chat_history, query):
    chat_history.first_query = query
    db.session.commit()


def perform_search(user_query, current_user):
    search_start_time = time.time()
    keywords = user_query.split()
    search_results = search_reviews(keywords, 1, 5, current_user)
    search_results = format_search_results(search_results)
    search_time = time.time() - search_start_time
    return search_results, search_time


def format_search_results(search_results):
    return [{
        'review_id': result.id,
        'author_name': result.author.username if result.author and not result.is_anonymous else 'Anonymous',
        'author_id': result.author.id if result.author and not result.is_anonymous else None,
        'course_name': result.course.name,
        'course_id': result.course.id,
        'content': result.content,
        'course_name_with_teachers': result.course.name_with_teachers_short,
        'rate': result.rate,
        'publish_time': result.publish_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': result.update_time.strftime('%Y-%m-%d %H:%M:%S'),
    } for result in search_results.items]


def generate_context(search_results):
    return "\n".join("\n".join([
        f"Review {i+1}:",
        f"Author: {result['author_name']}",
        f"Course: {result['course_name_with_teachers']}",
        f"Rate: {result['rate']}/10",
        f"=== Begin of Review ===",
        f"{result['content']}",
        f"=== End of Review ===",
        f"\n",
    ]) for i, result in enumerate(search_results))

def generate_response(chat_history_id, chat_messages, search_results, search_time, context):
    first_token_time = None
    start_time = time.time()

    # Remove content from search results before sending and saving
    search_results_without_content = [{**result, 'content': None} for result in search_results]

    yield f"data: {json.dumps({'type': 'search_results', 'content': search_results_without_content, 'search_time': search_time})}\n\n"

    ai_response = ""
    for token in call_openai(chat_messages):
        if first_token_time is None:
            first_token_time = time.time() - start_time
        ai_response += token
        yield f"data: {json.dumps({'type': 'ai_response', 'content': token})}\n\n"
    
    total_response_time = time.time() - start_time + search_time

    yield f"data: {json.dumps({'type': 'timing_info', 'search_time': search_time, 'time_to_first_token': first_token_time, 'total_response_time': total_response_time})}\n\n"

    save_ai_response(chat_history_id, ai_response, search_time, first_token_time, total_response_time, context, search_results_without_content)


def save_ai_response(chat_history_id, ai_response, search_time, first_token_time, total_response_time, context, search_results):
    with app.app_context():
        new_db_session = db.session()
        try:
            ai_message = ChatMessage(chat_history_id=chat_history_id, role='assistant', content=ai_response)
            ai_message.search_time = search_time
            ai_message.time_to_first_token = first_token_time
            ai_message.total_response_time = total_response_time
            ai_message.context = context
            ai_message.search_results = json.dumps(search_results)
            new_db_session.add(ai_message)
            new_db_session.commit()
        except Exception as e:
            new_db_session.rollback()
            print(f"Error saving AI response: {str(e)}")
        finally:
            new_db_session.close()

def handle_error(e):
    traceback.print_exc()
    return jsonify({'error': str(e)}), 400


@chat.route('/chat_history/<int:conversation_id>', methods=['GET'])
def get_chat_history(conversation_id):
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None
    
    chat_history = ChatHistory.query.filter_by(user_id=user_id, session_id=session_id, id=conversation_id).first()
    if not chat_history:
        return jsonify([])
    
    messages = ChatMessage.query.filter_by(chat_history_id=chat_history.id).order_by(ChatMessage.created_at).all()
    return jsonify([{
        'role': msg.role, 
        'content': msg.content,
        'search_time': msg.search_time,
        'time_to_first_token': msg.time_to_first_token,
        'total_response_time': msg.total_response_time,
        'search_results': msg.search_results,
    } for msg in messages])


@chat.route('/conversations', methods=['GET'])
def get_conversations():
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None

    conversations = ChatHistory.query.filter_by(user_id=user_id, session_id=session_id).order_by(ChatHistory.updated_at.desc()).all()
    
    result = []
    for conv in conversations:
        message_count = conv.messages.count()
        if message_count > 0 or conv == conversations[0]:
            result.append({
                'id': conv.id,
                'created_at': conv.created_at,
                'updated_at': conv.updated_at,
                'message_count': message_count,
                'first_query': conv.first_query,
            })
    
    return jsonify(result)


@chat.route('/conversation', methods=['POST'])
def create_conversation():
    user_id = current_user.id if current_user.is_authenticated else None
    session_id = session.get('session_id') if user_id is None else None
    
    new_conversation = ChatHistory(user_id=user_id, session_id=session_id)
    db.session.add(new_conversation)
    db.session.commit()
    
    return jsonify({
        'id': new_conversation.id,
        'created_at': new_conversation.created_at,
        'updated_at': new_conversation.updated_at
    }), 201


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


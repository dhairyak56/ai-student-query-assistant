import os
import logging
import time
from functools import wraps
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize rate limiting
rate_limits = {}
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 10

# Configure Google Gemini API - Store key in environment variable
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    logger.warning("No GEMINI_API_KEY found in environment variables")
genai.configure(api_key=API_KEY)

# Define fallback responses
FALLBACK_RESPONSES = [
    "I'm sorry, I don't have that information at the moment.",
    "I couldn't process your question. Could you try rephrasing it?",
    "There seems to be a technical issue. Please try again later.",
    "I'm having trouble connecting to my knowledge base. Please try again shortly.",
    "I'm currently experiencing high demand. Please try your question again in a moment."
]

# Cache for storing recent responses to save API calls
response_cache = {}
CACHE_TTL = 3600  # 1 hour in seconds

def rate_limiter(f):
    """Rate limiting decorator"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Initialize or update rate limit data for this IP
        if client_ip not in rate_limits:
            rate_limits[client_ip] = {'count': 0, 'window_start': current_time}
        elif current_time - rate_limits[client_ip]['window_start'] >= RATE_LIMIT_WINDOW:
            # Reset if window has passed
            rate_limits[client_ip] = {'count': 0, 'window_start': current_time}
        
        # Increment request count
        rate_limits[client_ip]['count'] += 1
        
        # Check if rate limit exceeded
        if rate_limits[client_ip]['count'] > MAX_REQUESTS_PER_WINDOW:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({
                "answer": "You've sent too many requests. Please wait a moment before trying again.",
                "error": "Rate limit exceeded"
            }), 429
        
        return f(*args, **kwargs)
    return wrapper

def get_ai_response(question, retry_count=0):
    """Get AI response using Google Gemini API with retries and fallbacks"""
    # Check cache first
    cache_key = question.lower().strip()
    if cache_key in response_cache:
        cache_entry = response_cache[cache_key]
        if time.time() - cache_entry['timestamp'] < CACHE_TTL:
            logger.info(f"Cache hit for question: {question[:50]}...")
            return cache_entry['response']
    
    try:
        # Add context to the question
        prompt = f"""
        You are a helpful assistant for university students.
        Answer the following question concisely and accurately:
        
        {question}
        """
        
        # Try multiple models in order of preference
        models_to_try = ["gemini-1.5-pro", "gemini-pro"]
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                if hasattr(response, "text"):
                    answer = response.text.strip()
                    
                    # Cache the response
                    response_cache[cache_key] = {
                        'response': answer,
                        'timestamp': time.time()
                    }
                    
                    return answer
            except Exception as model_error:
                logger.warning(f"Error with model {model_name}: {model_error}")
                continue  # Try next model
        
        # If we've exhausted retries or all models failed
        if retry_count < 2:
            # Wait briefly and retry
            time.sleep(1)
            return get_ai_response(question, retry_count + 1)
        else:
            # Return a fallback response if all retries and models failed
            import random
            return random.choice(FALLBACK_RESPONSES)

    except Exception as e:
        logger.error(f"Google API Error: {e}")
        if retry_count < 2:
            # Wait longer for quota issues
            time.sleep(2)
            return get_ai_response(question, retry_count + 1)
        else:
            import random
            return random.choice(FALLBACK_RESPONSES)

@app.route("/query", methods=["POST"])
@rate_limiter
def query():
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("No JSON data in request")
            return jsonify({"error": "Missing request data", "answer": "I couldn't understand your request. Please try again."}), 400
            
        if "question" not in data:
            logger.warning("Missing question in request")
            return jsonify({"error": "Missing question in request", "answer": "I couldn't find your question. Please try again."}), 400
            
        question = data.get("question", "").strip()
        
        if not question:
            logger.warning("Empty question received")
            return jsonify({"error": "Empty question", "answer": "Please type a question first."}), 400
            
        if len(question) > 500:
            logger.warning(f"Question too long: {len(question)} characters")
            return jsonify({"error": "Question too long (max 500 characters)", "answer": "Your question is too long. Please keep it under 500 characters."}), 400
        
        # Generate AI response
        try:
            logger.info(f"Generating AI response for: {question[:50]}...")
            answer = get_ai_response(question)
            
            # Even if there's an error in the AI response function, it should return a fallback message
            if not answer or not answer.strip():
                answer = "I'm sorry, I couldn't generate a response at this time."
                
            return jsonify({
                "answer": answer,
                "source": "AI"
            })
        except Exception as e:
            logger.error(f"Error while generating response: {e}")
            return jsonify({
                "answer": "I encountered a technical issue while processing your question. Please try again.",
                "error": str(e)
            }), 200  # Return 200 so the frontend still shows the error message
        
    except Exception as e:
        logger.error(f"Unexpected error in query endpoint: {e}")
        return jsonify({
            "answer": "I ran into an unexpected issue. Please try again later.",
            "error": "Server error"
        }), 200  # Return 200 so the frontend still shows the error message

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "API is running"}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting AI Student Query Assistant API")
    # Use environment variable for port if available
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)  # Set debug=False in production
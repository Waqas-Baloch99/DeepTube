import os
import json
import logging
from django.http import JsonResponse
from django.shortcuts import render
from groq import Groq

# Configure logging
logger = logging.getLogger(__name__)

# In-memory chat history (temporary per session)
CHAT_HISTORY = {}

def index(request):
    """Render the homepage."""
    if not request.session.session_key:
        request.session.create()
    return render(request, 'youtubeapp/index.html')

def script_generation(request):
    """Render the script generation page."""
    if not request.session.session_key:
        request.session.create()
    return render(request, 'youtubeapp/script_generation.html')

def chat_with_groq(request):
    """Handle chat requests with Groq API using DeepSeek model."""
    if request.method != 'POST':
        logger.warning("Invalid request method received")
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        if not user_message:
            logger.warning("No message provided in request")
            return JsonResponse({'error': 'No message provided'}, status=400)

        logger.info(f"Received message: {user_message}")

        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        if session_key not in CHAT_HISTORY:
            CHAT_HISTORY[session_key] = []

        CHAT_HISTORY[session_key].append({"role": "user", "content": user_message})
        if len(CHAT_HISTORY[session_key]) > 10:
            CHAT_HISTORY[session_key] = CHAT_HISTORY[session_key][-10:]

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            logger.error("GROQ_API_KEY environment variable is not set")
            raise ValueError("GROQ_API_KEY is not configured")

        client = Groq(api_key=api_key)
        logger.info("Groq client initialized successfully")

        messages = [
            {
                "role": "system",
                "content": "You are DeepSeek AI, a helpful assistant focused on video content creation and YouTube strategy. Use the chat history to provide context-aware responses."
            }
        ] + CHAT_HISTORY[session_key]

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="deepseek-r1-distill-llama-70b",
            temperature=0.3,
            max_tokens=1000,
        )

        response = chat_completion.choices[0].message.content
        logger.info("Groq API call successful")

        CHAT_HISTORY[session_key].append({"role": "assistant", "content": response})
        return JsonResponse({'response': response})

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in chat_with_groq: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)

def generate_script(request):
    """Generate a video script using DeepSeek model."""
    if request.method != 'POST':
        logger.warning("Invalid request method received")
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        topic = data.get('topic', '').strip()
        length = data.get('length', '')
        tone = data.get('tone', '')
        audience = data.get('audience', '')
        broll = data.get('broll', False)
        music = data.get('music', False)
        cta = data.get('cta', False)

        if not topic or not length or not tone:
            logger.warning("Missing required fields in script generation request")
            return JsonResponse({'error': 'Topic, length, and tone are required'}, status=400)

        logger.info(f"Generating script for topic: {topic}, length: {length}, tone: {tone}")

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            logger.error("GROQ_API_KEY environment variable is not set")
            raise ValueError("GROQ_API_KEY is not configured")

        client = Groq(api_key=api_key)
        logger.info("Groq client initialized successfully")

        # Construct prompt for DeepSeek
        prompt = f"""
        You are DeepSeek AI, an expert in video content creation. Generate a YouTube video script with the following details:
        - Topic: {topic}
        - Length: {length} (adjust content to fit approximate duration)
        - Tone: {tone}
        - Target Audience: {audience or 'General audience'}
        - Include B-roll suggestions: {broll}
        - Include Music recommendations: {music}
        - Include Call-to-Action: {cta}
        - Create a Video Description that include tag also like #tech 

        Format the script with clear sections:
        1. [Opening Hook] - Grab attention
        2. [Main Content] - Core message with optional B-roll
        3. [Conclusion] - Wrap-up with optional CTA and music
        4. [Video Description] - Include tags and relevant links
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are DeepSeek AI, an expert in video content creation."},
                {"role": "user", "content": prompt}
            ],
            model="deepseek-r1-distill-llama-70b",
            temperature=0.3,
            max_tokens=1500,  # Increased for longer scripts
        )

        script = chat_completion.choices[0].message.content
        logger.info("Script generation successful")
        return JsonResponse({'script': script})

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in generate_script: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred. Please try again.'}, status=500)

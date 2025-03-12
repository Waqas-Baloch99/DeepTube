from django.http import JsonResponse
from django.shortcuts import render
import logging
import json
import os
from groq import Groq
from django.core.cache import cache

# Configure logging
logger = logging.getLogger(__name__)

def get_groq_client():
    """Initialize and return Groq client."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY environment variable is not set")
        raise ValueError("GROQ_API_KEY is not configured")
    return Groq(api_key=api_key)

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
def chat_with_deepseek(request):
    """Handle chat requests with Groq API for assistance only."""
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

        # Use cache for chat history
        chat_history = cache.get(session_key, [])
        chat_history.append({"role": "user", "content": user_message})
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]
        cache.set(session_key, chat_history, timeout=3600)

        client = get_groq_client()
        logger.info("Groq client initialized successfully")

        messages = [
            {
                "role": "system",
                "content": "You are DeepSeek AI, a helpful assistant focused on video content creation and YouTube strategy. Provide assistance and answers only. If asked about generating a script, direct the user to the script generation page without generating it here. Use the chat history for context-aware responses."
            }
        ] + chat_history

        # Check for script generation request
        if "generate script" in user_message.lower() or "script generation" in user_message.lower():
            response = "For script generation, please visit the 'Generate Content' page by clicking the link in the navigation bar!"
            chat_history.append({"role": "assistant", "content": response})
            cache.set(session_key, chat_history, timeout=3600)
            return JsonResponse({'response': response})

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="deepseek-r1-distill-llama-70b",  # Specified model
            temperature=0.3,
            max_tokens=1000,
        )

        response = chat_completion.choices[0].message.content
        logger.info("Groq API call successful")

        chat_history.append({"role": "assistant", "content": response})
        cache.set(session_key, chat_history, timeout=3600)

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
    """Generate a video script using the Groq API."""
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

        client = get_groq_client()
        logger.info("Groq client initialized successfully")

        prompt = f"""
        You are DeepSeek AI, an expert in video content creation. Generate a detailed YouTube video script with the following details:
        - Topic: {topic}
        - Length: {length} (Short: 100-300 words, Medium: 500-1000 words, Long: 1000+ words)
        - Tone: {tone} (adapt vocabulary and style accordingly)
        - Target Audience: {audience or 'General audience'} (tailor content to their interests and knowledge level)
        - Include B-roll suggestions: {broll} (provide 2-3 specific, relevant examples per section if true)
        - Include Music recommendations: {music} (suggest mood-appropriate tracks or genres if true)
        - Include Call-to-Action: {cta} (craft a compelling, audience-specific CTA if true)
        - Create a Video Description that includes relevant tags (e.g., #tech, #education)

        Format the script with clear sections:
        1. [Opening Hook] - A 15-30 second attention-grabbing intro with a strong hook
        2. [Main Content] - Break into 2-3 subsections with clear transitions; include optional B-roll
        3. [Conclusion] - A concise wrap-up with optional CTA and music suggestions
        4. [Video Description] - Include a 2-3 sentence summary, tags, and relevant links
        
        Ensure the script is engaging, concise, and matches the specified tone and length.
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are DeepSeek AI, an expert in video content creation."},
                {"role": "user", "content": prompt}
            ],
            model="deepseek-r1-distill-llama-70b",  # Specified model
            temperature=0.3,
            max_tokens=1500,
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

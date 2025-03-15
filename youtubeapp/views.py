from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
import logging
import json
import os
from datetime import datetime, timedelta
from groq import Groq
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

# Constants
CACHE_TIMEOUT = 3600  # 1 hour in seconds
HISTORY_TIMEOUT = 86400  # 24 hours in seconds
MAX_TRENDS = 5

# Load environment variables from .env file
load_dotenv()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Initialize Groq client (assuming DeepSeek is simulated via Groq)
groq_client = None
try:
    if GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")

def get_groq_client():
    """Initialize and return Groq client."""
    global groq_client
    if groq_client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        groq_client = Groq(api_key=GROQ_API_KEY)
    return groq_client
# views.py - Updated with Enhanced Error Handling and Prompt Engineering
@csrf_exempt
def index(request):
    """Render chat interface and handle chat requests."""
    session_key = request.session.session_key or ""
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    
    chat_history = cache.get(f"chat_history_{session_key}", [])
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            query = data.get('message', '').strip()
            if not query:
                return JsonResponse({'error': 'Message is required'}, status=400)

            # Enhanced error handling for Groq client
            try:
                client = get_groq_client()
            except Exception as e:
                logger.error(f"Groq client initialization failed: {str(e)}")
                return JsonResponse({'error': 'AI service configuration error'}, status=500)

            # Optimized system prompt
            system_prompt = """ You are DeepSeek-R1 Assistant a youtube strategy expert .
                    For script generation, redirect to the dedicated tool"""

            try:
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    model="deepseek-r1-distill-llama-70b",
                    temperature=0.4,
                    timeout=10  # Add timeout
                )
            except Exception as e:
                logger.error(f"Groq API Error: {str(e)}")
                return JsonResponse({
                    'error': 'AI service temporarily unavailable',
                    'retry_after': 30
                }, status=503)

            # Process response
            if not response.choices:
                logger.error("Empty response from AI model")
                return JsonResponse({'error': 'Empty AI response'}, status=500)

            response_content = response.choices[0].message.content

            # Save to chat history with size limit
            chat_history.append({
                "user": query,
                "bot": response_content,
                "timestamp": datetime.now().isoformat()
            })
            cache.set(f"chat_history_{session_key}", chat_history[-10:], HISTORY_TIMEOUT)  # Keep last 10 messages

            return JsonResponse({
                'response': response_content,
                'model': 'deepseek-r1-distill-llama-70b-specdec',
                'timestamp': datetime.now().isoformat()
            })

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            return JsonResponse({'error': 'Invalid request format'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Service interruption'}, status=500)

    # GET request remains unchanged
    context = {
        'model_name': 'DeepSeek-R1',
        'chat_features': ['Smart Insights', 'Voice Chat', 'AI-Powered'],
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chat_history': chat_history,
    }
    return render(request, 'youtubeapp/index.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def clear_chat_history(request):
    """Clear user's chat history."""
    session_key = request.session.session_key or ""
    cache.delete(f"chat_history_{session_key}")
    return JsonResponse({'status': 'History cleared'})

def youtube_analytics(request):
    """Render YouTube analytics page with trending videos."""
    region_code = request.session.get('region_code', 'US')
    cache_key = f'youtube_trending_data_{region_code}'
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        trending_videos = get_youtube_trending(YOUTUBE_API_KEY, region_code)
        if trending_videos:
            cache.set(cache_key, {'trending_videos': trending_videos}, CACHE_TIMEOUT)
    else:
        trending_videos = cached_data['trending_videos']

    context = {
        'countries': get_available_countries(),
        'region_code': region_code,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'trending_videos': trending_videos if trending_videos else [],
    }
    return render(request, 'youtubeapp/youtube_analytics.html', context)

def get_youtube_trending(api_key, region_code='US', max_results=MAX_TRENDS):
    """Fetch trending YouTube videos with additional details."""
    if not api_key:
        logger.error("YouTube API key not found")
        return None
    
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    try:
        trending_request = youtube.videos().list(
            part='snippet,statistics',
            chart='mostPopular',
            regionCode=region_code,
            maxResults=max_results
        )
        trending_response = trending_request.execute()
        trending_videos = []

        for item in trending_response['items']:
            snippet = item['snippet']
            stats = item['statistics']
            video_id = item['id']
            trending_videos.append({
                'title': snippet['title'],
                'channel': snippet['channelTitle'],
                'video_id': video_id,
                'thumbnail': snippet['thumbnails']['medium']['url'],
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'description': snippet.get('description', 'No description available'),
                'view_count': stats.get('viewCount', 'N/A')
            })

        return trending_videos

    except HttpError as e:
        logger.error(f"Failed to fetch YouTube trending videos: {e}")
        return None

@csrf_exempt
@require_http_methods(["POST"])
def update_region(request):
    """Update trending videos based on selected region."""
    try:
        data = json.loads(request.body)
        region_code = data.get('region_code', 'US')
        trending_videos = get_youtube_trending(YOUTUBE_API_KEY, region_code=region_code)
        
        if not trending_videos:
            return JsonResponse({'error': 'Failed to fetch videos for this region'}, status=500)
        
        cache_key = f'youtube_trending_data_{region_code}'
        cache.set(cache_key, {'trending_videos': trending_videos}, CACHE_TIMEOUT)
        
        return JsonResponse({'trending_videos': trending_videos})
    except Exception as e:
        logger.error(f"Failed to update region: {e}")
        return JsonResponse({'error': 'Invalid request'}, status=400)

def script_generation(request):
    """Render script generation interface."""
    context = {
        'model_version': 'DeepSeek-R1-Enhanced',
        'supported_features': ['music_recommendations', 'seo_optimization']
    }
    if not request.session.session_key:
        request.session.create()
    return render(request, 'youtubeapp/script_generation.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def generate_script(request):
    """Generate YouTube video script using DeepSeek-R1."""
    try:
        if not request.body:
            logger.warning("Received empty request body")
            return JsonResponse({'error': 'Request body is empty'}, status=400)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in request body")
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)

        topic = data.get('topic', '').strip()
        if not topic:
            logger.warning("No topic provided in request")
            return JsonResponse({'error': 'Topic is required'}, status=400)

        keywords = data.get('keywords', '').strip()
        music = bool(data.get('music', False))

        logger.info(f"Generating script for topic: {topic}")
        client = get_groq_client()

        prompt = f"""
        [DeepSeek-R1 Instruction Set]
        ROLE: Elite YouTube Content Architect
        TASK: Generate high-performance video script
        FORMAT: Structured YouTube blueprint
        
        CONTENT PARAMETERS:
        - Primary Topic: {topic}
        - Secondary Keywords: {keywords or 'auto-generated'}
        - Target Metrics: Retention >70%, CTR >8%
        - Music Integration: {'Enabled' if music else 'Disabled'}
        
        OUTPUT REQUIREMENTS:
        1. TITLE: SEO-optimized (<100 chars), include primary keyword
        2. HOOK (0:00-0:30): Viral potential opener
        3. INTRO (0:30-1:00): Value proposition + agenda
        4. MAIN SECTIONS (3-4 parts):
           - Clear timestamps
           - Visual transition cues
           - Engagement triggers
        5. CONCLUSION: CTA + retention loop
        6. DESCRIPTION: 
           - First 150 chars: Search-optimized
           - Full summary: 500 chars max
           - Hashtags: 5-8 trending
           - Timestamp markers
           - Discussion prompts
        """

        system_prompt = """
        You are DeepSeek-R1, an advanced AI content architect for YouTube.
        Optimize scripts for viewer retention and engagement using viral patterns
        and platform algorithms. Use a professional yet accessible tone.
        """

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            model="deepseek-r1-distill-llama-70b",  # Placeholder; replace with actual DeepSeek model if available
            temperature=0.6,
            max_tokens=2500,
            top_p=0.9,
        )

        script_data = {
            'id': int(datetime.now().timestamp()),
            'script': response.choices[0].message.content,
            'topic': topic,
            'created_at': datetime.now().isoformat(),
            'metadata': {
                'model': 'DeepSeek-R1',
                'version': '1.2.1',
                'music_enabled': music,
            }
        }

        session_key = request.session.session_key
        history = cache.get(f"script_history_{session_key}", [])
        cache.set(f"script_history_{session_key}", [script_data] + history[:4], HISTORY_TIMEOUT)

        return JsonResponse({
            'script': script_data['script'],
            'metadata': script_data['metadata']
        })

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return JsonResponse({'error': 'Server configuration issue'}, status=500)
    except Exception as e:
        logger.error(f"Script generation failed: {str(e)}")
        return JsonResponse({'error': 'Script generation failed'}, status=500)

@require_http_methods(["GET"])
def get_script_history(request):
    """Retrieve user's script generation history."""
    session_key = request.session.session_key or ""
    history = cache.get(f"script_history_{session_key}", [])
    return JsonResponse({
        'history': [
            {
                'id': item['id'],
                'preview': item['script'][:75],
                'topic': item['topic'],
                'created_at': item['created_at']
            }
            for item in history
        ]
    })

@require_http_methods(["GET"])
def get_script(request, script_id):
    """Retrieve a specific generated script by ID."""
    session_key = request.session.session_key or ""
    history = cache.get(f"script_history_{session_key}", [])
    script = next((item for item in history if item['id'] == int(script_id)), None)
    if script:
        return JsonResponse(script)
    return JsonResponse({'error': 'Script not found'}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def clear_script_history(request):
    """Clear user's script generation history."""
    session_key = request.session.session_key or ""
    cache.delete(f"script_history_{session_key}")
    return JsonResponse({'status': 'History cleared'})

def contact_view(request):
    """Render contact page and handle form submission."""
    if request.method == 'POST':
        # Handle form submission here
        pass
    return render(request, 'youtubeapp/contact.html')

def get_available_countries():
    """Placeholder for country list - implement as needed."""
    return ['US', 'UK', 'CA', 'AU']

def home(request):
    """Render the DeepTube homepage."""
    context = {
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    return render(request, 'youtubeapp/home.html', context)

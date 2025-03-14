# views.py
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
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

# Constants
CACHE_TIMEOUT = 3600  # 1 hour in seconds
HISTORY_TIMEOUT = 86400  # 1 day in seconds
TREND_TIMEFRAME = 'today 3-m'
MAX_TRENDS = 5

def get_groq_client():
    """Initialize Groq client with API key validation."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY not found in environment variables")
        raise ValueError("GROQ_API_KEY is required")
    return Groq(api_key=api_key)

def get_google_trends():
    """Fetch and process Google Trends data."""
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        daily_trends = pytrends.today_searches(pn='US')
        
        if daily_trends.empty:
            logger.warning("No trends returned from Google Trends")
            return []

        pytrends.build_payload(
            kw_list=list(daily_trends[:MAX_TRENDS]),
            cat=0,
            timeframe=TREND_TIMEFRAME,
            geo='US'
        )
        interest_data = pytrends.interest_over_time()
        
        trends = [
            {
                'name': trend,
                'count': int(interest_data[trend].mean()),
                'growth': f"+{int(interest_data[trend].pct_change().mean() * 100)}%"
            }
            for trend in daily_trends[:MAX_TRENDS * 2] 
            if trend in interest_data.columns
        ]
        return trends[:MAX_TRENDS]
    
    except Exception as e:
        logger.error(f"Failed to fetch Google Trends: {str(e)}")
        return []

def index(request):
    """Render homepage with AI features and trending topics."""
    context = {
        'ai_model': 'DeepSeek-R1',
        'features': [
            "AI-Powered Script Generation",
            "Trend-Driven Content Creation",
            "Audience Engagement Analytics",
            "Cross-Platform Optimization"
        ],
        'trends': [],
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    
    trends = cache.get('google_trends')
    if trends is None:
        trends = get_google_trends()
        cache.set('google_trends', trends, CACHE_TIMEOUT)
    
    context['trends'] = trends
    context['sample_data'] = not bool(trends)
    
    if not request.session.session_key:
        request.session.create()
    
    return render(request, 'youtubeapp/index.html', context)

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
            model="deepseek-r1-distill-llama-70b",
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

@csrf_exempt
@require_http_methods(["POST"])
def chat_with_deepseek(request):
    """Provide YouTube strategy advice via DeepSeek-R1."""
    try:
        data = json.loads(request.body)
        query = data.get('message', '').strip()
        if not query:
            return JsonResponse({'error': 'Message is required'}, status=400)

        client = get_groq_client()
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are DeepSeek-R1 Assistant, a YouTube strategy expert.
                    For script generation, redirect to the dedicated tool.
                    """
                },
                {"role": "user", "content": query}
            ],
            model="deepseek-r1-distill-llama-70b",
            temperature=0.4,
            max_tokens=800
        )

        return JsonResponse({
            'response': response.choices[0].message.content,
            'model': 'DeepSeek-R1',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return JsonResponse({'error': 'Chat service unavailable'}, status=503)

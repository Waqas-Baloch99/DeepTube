from django.shortcuts import render

def index(request):
    return render(request, 'youtubeapp/index.html')

def script_genertation(request):
    return render(request, 'youtubeapp/script_genertation.html')
# Create your views here.

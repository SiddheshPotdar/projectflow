from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Project
from .forms import ProjectForm

def home(request):
    # If user is authenticated, show dashboard; else show welcome page
    if request.user.is_authenticated:
        return dashboard(request)
    else:
        return render(request, 'projects/home.html')

@login_required
def dashboard(request):
    # Get statistics
    active_count = Project.objects.filter(status='active', members=request.user).count()
    completed_count = Project.objects.filter(status='completed', members=request.user).count()
    on_hold_count = Project.objects.filter(status='on_hold', members=request.user).count()
    
    # Handle project creation form
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            project.members.add(request.user)  # creator is automatically a member
            messages.success(request, f'Project "{project.name}" created successfully!')
            return redirect('home')
    else:
        form = ProjectForm()
    
    # Get user's projects (where they are a member)
    projects = Project.objects.filter(members=request.user).order_by('-created_at')
    
    context = {
        'form': form,
        'projects': projects,
        'active_count': active_count,
        'completed_count': completed_count,
        'on_hold_count': on_hold_count,
    }
    return render(request, 'projects/dashboard.html', context)

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome aboard.')
            return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})
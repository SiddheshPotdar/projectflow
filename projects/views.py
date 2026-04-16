from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import Project, Task, Comment
from .forms import ProjectForm, ProjectEditForm, TaskForm, CommentForm
from django.db.models import Q

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_project_update(project_id, event_type, data):
    """Send a real-time update to all clients in the project room."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'project_{project_id}',
        {
            'type': 'project_update',
            'data': {
                'type': event_type,
                **data
            }
        }
    )
def home(request):
    if request.user.is_authenticated:
        return dashboard(request)
    else:
        return render(request, 'projects/home.html')

@login_required
def dashboard(request):
    # Statistics
    active_count = Project.objects.filter(status='active', members=request.user).count()
    completed_count = Project.objects.filter(status='completed', members=request.user).count()
    on_hold_count = Project.objects.filter(status='on_hold', members=request.user).count()
    
    # Project creation
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.status = 'active'  # force new projects to be active
            project.save()
            project.members.add(request.user)
            messages.success(request, f'Project "{project.name}" created successfully!')
            return redirect('home')
    else:
        form = ProjectForm()
    
    # Get search query
    query = request.GET.get('q', '').strip()
    projects = Project.objects.filter(members=request.user)

    if query:
        projects = projects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    projects = projects.order_by('-created_at')
    
    context = {
        'form': form,
        'projects': projects,
        'active_count': active_count,
        'completed_count': completed_count,
        'on_hold_count': on_hold_count,
        'search_query': query,   # add this
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

# ============== PROJECT VIEWS ==============
@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    # Ensure user is a member
    if request.user not in project.members.all():
        return HttpResponseForbidden("You don't have access to this project.")
    
    tasks = project.tasks.all().order_by('-created_at')
    
    # Organize tasks by status for Kanban columns
    todo_tasks = tasks.filter(status='todo')
    in_progress_tasks = tasks.filter(status='in_progress')
    done_tasks = tasks.filter(status='done')
    
    task_form = TaskForm(project=project)
    
    context = {
        'project': project,
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'done_tasks': done_tasks,
        'task_form': task_form,
    }
    return render(request, 'projects/project_detail.html', context)

@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.created_by:
        messages.error(request, "Only the project creator can edit it.")
        return redirect('project_detail', pk=pk)
    
    if request.method == 'POST':
        form = ProjectEditForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated successfully.')
            return redirect('project_detail', pk=pk)
    else:
        form = ProjectEditForm(instance=project)
    
    return render(request, 'projects/project_form.html', {'form': form, 'project': project})

@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.created_by:
        messages.error(request, "Only the project creator can delete it.")
        return redirect('project_detail', pk=pk)
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project deleted successfully.')
        return redirect('home')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})

# ============== TASK VIEWS ==============
@login_required
def task_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.user not in project.members.all():
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = TaskForm(request.POST, project=project)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.created_by = request.user
            task.status = 'todo'
            task.save()
            broadcast_project_update(project.id, 'task_created', {
                'task_id': task.id,
                'title': task.title,
                'status': task.status,
                'assigned_to': task.assigned_to.username if task.assigned_to else None,
                'due_date': task.due_date.isoformat() if task.due_date else None,
            })
            messages.success(request, 'Task added successfully.')
            return redirect('project_detail', pk=project.pk)
        else:
            # Form invalid – re-render project detail with errors
            tasks = project.tasks.all().order_by('-created_at')
            todo_tasks = tasks.filter(status='todo')
            in_progress_tasks = tasks.filter(status='in_progress')
            done_tasks = tasks.filter(status='done')
            
            context = {
                'project': project,
                'todo_tasks': todo_tasks,
                'in_progress_tasks': in_progress_tasks,
                'done_tasks': done_tasks,
                'task_form': form,  # pass the bound form with errors
            }
            return render(request, 'projects/project_detail.html', context)
    else:
        # GET request shouldn't happen here, but just in case redirect
        return redirect('project_detail', pk=project.pk)

@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.user not in task.project.members.all():
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, project=task.project)
        if form.is_valid():
            form.save()
            broadcast_project_update(task.project.id, 'task_updated', {
                'task_id': task.id,
                'title': task.title,
                'status': task.status,
                'assigned_to': task.assigned_to.username if task.assigned_to else None,
                'due_date': task.due_date.isoformat() if task.due_date else None,
            })
            messages.success(request, 'Task updated successfully.')
            return redirect('project_detail', pk=task.project.pk)
    else:
        form = TaskForm(instance=task, project=task.project)
    
    return render(request, 'projects/task_form.html', {'form': form, 'task': task, 'project': task.project})

@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.user not in task.project.members.all():
        return HttpResponseForbidden()
    
    project_pk = task.project.pk
    if request.method == 'POST':
        task.delete()
        broadcast_project_update(project_pk, 'task_deleted', {
            'task_id': pk,
        })
        messages.success(request, 'Task deleted successfully.')
        return redirect('project_detail', pk=project_pk)
    return render(request, 'projects/task_confirm_delete.html', {'task': task})

# ============== COMMENT VIEWS ==============
@login_required
def comment_create(request, task_pk):
    task = get_object_or_404(Task, pk=task_pk)
    if request.user not in task.project.members.all():
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.user = request.user
            comment.save()
            broadcast_project_update(task.project.id, 'comment_added', {
                'task_id': task.id,
                'comment_id': comment.id,
                'username': request.user.username,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
            })
            messages.success(request, 'Comment added.')
    return redirect('project_detail', pk=task.project.pk)
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Candidate, Vote,Election

def home_view(request):
    return render(request, 'home.html')


def about(request):
    return render(request, 'about.html')

def forgot_password_view(request):
    return render(request, 'forgot_password.html')


# ─── REGISTER ──────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email    = request.POST.get('email')
        password = request.POST.get('password')
        confirm  = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'registration.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return render(request, 'registration.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'registration.html')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, 'Account created! Please login.')
        return redirect('login')

    return render(request, 'registration.html')


# ─── LOGIN ─────────────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password!')

    return render(request, 'login.html')


# ─── LOGOUT ────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')


# ─── DASHBOARD ─────────────────────────────────────────────────
@login_required(login_url='login')
def dashboard_view(request):
    election    = Election.objects.filter(is_active=True).first()
    candidates  = Candidate.objects.all()
    total_votes = Vote.objects.count()
    user_voted  = Vote.objects.filter(user=request.user).exists()
    user_vote   = Vote.objects.filter(user=request.user).first()

    # Can user vote?
    can_vote = False
    if election and election.is_ongoing() and not user_voted:
        can_vote = True

    return render(request, 'dashboard.html', {
        'candidates'  : candidates,
        'total_votes' : total_votes,
        'user_voted'  : user_voted,
        'user_vote'   : user_vote,
        'election'    : election,
        'can_vote'    : can_vote,
        'time_seconds': election.time_remaining_seconds() if election else 0,
    })


# ─── VOTE ──────────────────────────────────────────────────────
@login_required(login_url='login')
def vote_view(request):
    if request.method == 'POST':

        # Check election is ongoing
        election = Election.objects.filter(is_active=True).first()
        if not election or not election.is_ongoing():
            messages.error(request, 'Voting is not allowed right now!')
            return redirect('dashboard')

        # Already voted?
        if Vote.objects.filter(user=request.user).exists():
            messages.error(request, 'You have already voted!')
            return redirect('dashboard')

        candidate_id = request.POST.get('candidate_id')
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            messages.error(request, 'Invalid candidate!')
            return redirect('dashboard')

        Vote.objects.create(user=request.user, candidate=candidate)
        candidate.votes += 1
        candidate.save()
        messages.success(request, f'Vote cast for {candidate.name}!')
        return redirect('results')

    return redirect('dashboard')


# ─── RESULTS ───────────────────────────────────────────────────
@login_required(login_url='login')
def results_view(request):
    candidates  = Candidate.objects.all().order_by('-votes')
    total_votes = Vote.objects.count()
    winner      = candidates.first() if candidates.exists() else None
    election    = Election.objects.filter(is_active=True).first()

    return render(request, 'results.html', {
        'candidates' : candidates,
        'total_votes': total_votes,
        'winner'     : winner,
        'election'   : election,
    })
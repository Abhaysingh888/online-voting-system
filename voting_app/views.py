import random
import hashlib
import hmac
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.core.cache import cache
from django.db import models
from django.db.models import Count

from .models import Candidate, Vote, Election, VoterProfile

logger = logging.getLogger('voting')


# ================= CONSTANTS =================
OTP_MAX_ATTEMPTS = 5
OTP_LOCKOUT_SECS = 900
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECS = 900


# ================= OTP UTILS =================
def generate_otp():
    return str(random.SystemRandom().randint(100000, 999999))


def hash_otp(otp, email):
    key = settings.SECRET_KEY.encode()
    msg = f"{otp}:{email}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def send_otp_email(email, otp, purpose="verification"):
    subject = "VoteSecure — Verification Code"
    message = (
        f"Your OTP for {purpose} is: {otp}\n"
        f"Valid for 10 minutes. Do not share this with anyone."
    )
    send_mail(subject, message, settings.EMAIL_HOST_USER, [email], fail_silently=False)


# ================= RATE LIMITING =================
def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def is_rate_limited(key, max_attempts, lockout_secs):
    return cache.get(key, 0) >= max_attempts


def increment_attempts(key, lockout_secs):
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, lockout_secs)
    return attempts


def reset_attempts(key):
    cache.delete(key)


# ================= HOME & STATIC =================
def home_view(request):
    elections = Election.objects.filter(is_active=True).order_by('-start_time')[:3]
    return render(request, 'home.html', {'elections': elections})


def about_view(request):
    return render(request, 'about.html')


# ================= REGISTER =================
@never_cache
@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        aadhar = request.POST.get('aadhar_no', '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')

        if not all([username, email, aadhar, password, confirm]):
            messages.error(request, 'All fields are required!')
            return render(request, 'registration.html')

        if password != confirm:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'registration.html')

        if len(aadhar) != 12 or not aadhar.isdigit():
            messages.error(request, 'Aadhar number must be 12 digits!')
            return render(request, 'registration.html')

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            try:
                profile = VoterProfile.objects.get(user=existing_user)
                if not existing_user.is_active and not profile.is_verified:
                    profile.delete()
                    existing_user.delete()
                else:
                    messages.error(request, 'Email already registered!')
                    return render(request, 'registration.html')
            except VoterProfile.DoesNotExist:
                existing_user.delete()

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return render(request, 'registration.html')

        if VoterProfile.objects.filter(aadhar_no=aadhar).exists():
            messages.error(request, 'Aadhar number already registered!')
            return render(request, 'registration.html')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = False
        user.save()

        otp = generate_otp()
        VoterProfile.objects.create(
            user=user,
            aadhar_no=aadhar,
            otp=hash_otp(otp, email),
            otp_created=timezone.now(),
            is_verified=False,
        )

        try:
            send_otp_email(email, otp, "Registration")
        except Exception as e:
            logger.error(f"OTP email failed for {email}: {e}")
            user.delete()
            messages.error(request, 'Failed to send OTP. Try again later.')
            return render(request, 'registration.html')

        request.session['verify_email'] = email
        request.session['verify_purpose'] = 'register'
        request.session.set_expiry(900)

        return redirect('verify_otp')

    return render(request, 'registration.html')


# ================= VERIFY OTP =================
@never_cache
@require_http_methods(["GET", "POST"])
def verify_otp_view(request):
    email = request.session.get('verify_email')
    purpose = request.session.get('verify_purpose', 'register')

    if not email:
        return redirect('login')

    try:
        user = User.objects.get(email=email)
        profile = VoterProfile.objects.get(user=user)
    except (User.DoesNotExist, VoterProfile.DoesNotExist):
        messages.error(request, 'Session invalid. Please register again.')
        return redirect('register')

    if request.method == 'GET':
        return render(request, 'verify_otp.html', {'email': email})

    entered_otp = request.POST.get('otp', '').strip()

    if not entered_otp:
        messages.error(request, 'Please enter OTP.')
        return render(request, 'verify_otp.html', {'email': email})

    try:
        if not profile.is_otp_valid():
            messages.error(request, 'OTP expired! Please start over.')
            return redirect('register' if purpose == 'register' else 'login')
    except Exception as e:
        print("OTP VALID ERROR:", e)
        messages.error(request, 'OTP error. Please try again.')
        return redirect('login')

    try:
        entered_hash = hash_otp(entered_otp, email)
    except Exception as e:
        print("HASH ERROR:", e)
        messages.error(request, 'Something went wrong.')
        return redirect('login')

    if not profile.otp or not hmac.compare_digest(profile.otp, entered_hash):
        messages.error(request, 'Invalid OTP! Please try again.')
        return render(request, 'verify_otp.html', {'email': email})

    if purpose == 'register':
        user.is_active = True
        user.save()
        profile.is_verified = True

    profile.otp = ''
    profile.save()

    request.session.pop('verify_email', None)
    request.session.pop('verify_purpose', None)

    if purpose == 'login':
        login(request, user)
        logger.info(f"User {user.username} logged in via OTP.")
        return redirect('dashboard')

    messages.success(request, 'Account verified! You can now log in.')
    return redirect('login')


# ================= LOGIN =================
@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        ip = get_client_ip(request)
        rate_key = f"login_attempts:{ip}"

        if is_rate_limited(rate_key, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECS):
            messages.error(request, 'Too many failed attempts. Try again in 15 minutes.')
            return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)

        if user is None:
            increment_attempts(rate_key, LOGIN_LOCKOUT_SECS)
            messages.error(request, 'Invalid username or password.')
            return render(request, 'login.html')

        reset_attempts(rate_key)

        try:
            profile = VoterProfile.objects.get(user=user)
        except VoterProfile.DoesNotExist:
            messages.error(request, 'Voter profile not found. Contact support.')
            return render(request, 'login.html')

        otp = generate_otp()
        profile.otp = hash_otp(otp, user.email)
        profile.otp_created = timezone.now()
        profile.save()

        try:
            send_otp_email(user.email, otp, "Login")
        except Exception as e:
            logger.error(f"Login OTP email failed for {user.email}: {e}")
            messages.error(request, 'Failed to send OTP. Try again.')
            return render(request, 'login.html')

        request.session['verify_email'] = user.email
        request.session['verify_purpose'] = 'login'
        request.session.set_expiry(900)

        return redirect('verify_otp')

    return render(request, 'login.html')


# ================= RESEND OTP =================
def resend_otp_view(request):
    email = request.session.get('verify_email')
    purpose = request.session.get('verify_purpose', 'register')

    if not email:
        return redirect('login')

    try:
        user = User.objects.get(email=email)
        profile = VoterProfile.objects.get(user=user)
    except (User.DoesNotExist, VoterProfile.DoesNotExist):
        return redirect('register')

    otp = generate_otp()
    profile.otp = hash_otp(otp, email)
    profile.otp_created = timezone.now()
    profile.save()

    try:
        send_otp_email(email, otp, purpose.capitalize())
        messages.success(request, 'New OTP sent to your email!')
    except Exception as e:
        messages.error(request, 'Failed to send OTP. Try again.')

    return redirect('verify_otp')


# ================= FORGOT PASSWORD =================
@never_cache
@require_http_methods(["GET", "POST"])
def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        try:
            user = User.objects.get(email=email)
            profile = VoterProfile.objects.get(user=user)

            otp = generate_otp()
            profile.otp = hash_otp(otp, email)
            profile.otp_created = timezone.now()
            profile.save()

            send_otp_email(email, otp, "Password Reset")

            request.session['verify_email'] = email
            request.session['verify_purpose'] = 'reset'
            request.session.set_expiry(900)

            messages.success(request, 'OTP sent to your email.')
            return redirect('verify_otp')

        except (User.DoesNotExist, VoterProfile.DoesNotExist):
            messages.success(request, 'If this email is registered, an OTP has been sent.')
            return render(request, 'forgot_password.html')

        except Exception as e:
            logger.error(f"Forgot password email error: {e}")
            messages.error(request, 'Failed to send OTP. Try again later.')

    return render(request, 'forgot_password.html')


# ================= DASHBOARD =================
@login_required
def dashboard_view(request):
    try:
        profile = VoterProfile.objects.get(user=request.user)
    except VoterProfile.DoesNotExist:
        return redirect('logout')

    election    = Election.objects.filter(is_active=True).first()
    candidates  = Candidate.objects.all()
    total_votes = Vote.objects.count()
    user_voted  = Vote.objects.filter(user=request.user).exists()
    user_vote   = Vote.objects.filter(user=request.user).select_related('candidate').first()

    time_seconds = 0
    if election and election.is_ongoing():
        time_seconds = election.time_remaining_seconds()

    context = {
        'profile':      profile,
        'election':     election,
        'candidates':   candidates,
        'total_votes':  total_votes,
        'user_voted':   user_voted,
        'user_vote':    user_vote,
        'can_vote':     election and election.is_ongoing() and not user_voted,
        'time_seconds': time_seconds,
    }
    return render(request, 'dashboard.html', context)


# ================= VOTE =================
@login_required
@require_http_methods(["GET", "POST"])
def vote_view(request):
    try:
        profile = VoterProfile.objects.get(user=request.user)
    except VoterProfile.DoesNotExist:
        messages.error(request, 'Voter profile not found.')
        return redirect('dashboard')

    election = Election.objects.filter(is_active=True).order_by('start_time').first()

    if not election:
        messages.info(request, 'No active election at the moment.')
        return redirect('dashboard')

    if not election.is_ongoing():
        if not election.has_started():
            messages.info(request, f'Election starts at {election.start_time.strftime("%d %b %Y, %I:%M %p")}.')
        else:
            messages.warning(request, 'This election has ended.')
        return redirect('dashboard')

    candidates = Candidate.objects.all()

    already_voted = Vote.objects.filter(user=request.user).exists()
    if already_voted:
        messages.warning(request, 'You have already cast your vote.')
        return redirect('results')

    if request.method == 'POST':
        candidate_id = request.POST.get('candidate_id')

        if not candidate_id:
            messages.error(request, 'Please select a candidate.')
            return render(request, 'vote.html', {'election': election, 'candidates': candidates, 'profile': profile})

        candidate = get_object_or_404(Candidate, id=candidate_id)

        if Vote.objects.filter(user=request.user).exists():
            messages.error(request, 'You have already voted!')
            return redirect('results')

        Vote.objects.create(user=request.user, candidate=candidate)
        Candidate.objects.filter(id=candidate.id).update(votes=models.F('votes') + 1)

        logger.info(f"Vote cast by {request.user.username} for candidate {candidate.name}")
        messages.success(request, f'Your vote for {candidate.name} has been recorded!')
        return redirect('results')

    return render(request, 'vote.html', {'election': election, 'candidates': candidates, 'profile': profile})


# ================= RESULTS =================
@login_required
def results_view(request):
    election   = Election.objects.filter(is_active=True).first()
    candidates = Candidate.objects.all().order_by('-votes')

    total_votes = Vote.objects.count()
    winner      = candidates.first() if candidates.exists() else None

    # ✅ Sirf election khatam hone ke baad results dikhao
    results_visible = election.has_ended() if election else False

    candidates_data = []
    for c in candidates:
        pct = round((c.votes / total_votes * 100), 1) if total_votes > 0 else 0
        candidates_data.append({
            'candidate':  c,
            'percentage': pct,
        })

    user_voted = Vote.objects.filter(user=request.user).exists()
    user_vote  = Vote.objects.filter(user=request.user).select_related('candidate').first()

    context = {
        'election':        election,
        'candidates':      candidates,
        'candidates_data': candidates_data,
        'total_votes':     total_votes,
        'winner':          winner,
        'user_voted':      user_voted,
        'user_vote':       user_vote,
        'results_visible': results_visible,  # ✅ Template mein use hoga
    }
    return render(request, 'results.html', context)


# ================= LOGOUT =================
def logout_view(request):
    username = request.user.username if request.user.is_authenticated else 'anonymous'
    logger.info(f"User {username} logged out.")
    logout(request)
    request.session.flush()
    return redirect('login')
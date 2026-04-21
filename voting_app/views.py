import random
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Candidate, Vote, Election, VoterProfile


# ── OTP Generator ──────────────────────────────────────────────
def generate_otp():
    return str(random.randint(100000, 999999))


# ── Send OTP Email ─────────────────────────────────────────────
def send_otp_email(email, otp, purpose="verification"):
    subject = f"VoteSecure — Your OTP for {purpose}"
    message = f"""
Dear Voter,

Your One-Time Password (OTP) for VoteSecure {purpose} is:

        {otp}

This OTP is valid for 10 minutes only.
Do NOT share this OTP with anyone.

If you did not request this, please ignore this email.

— VoteSecure Team
    """
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )


# ── HOME ───────────────────────────────────────────────────────
def home_view(request):
    return render(request, 'home.html')

def about_view(request):
    return render(request, 'about.html')


# ── FORGOT PASSWORD ────────────────────────────────────────────
def forgot_password_view(request):
    return render(request, 'forgot_password.html')


# ══════════════════════════════════════════════════════════════
# REGISTRATION — Step 1: Fill form
# ══════════════════════════════════════════════════════════════
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username  = request.POST.get('username', '').strip()
        email     = request.POST.get('email', '').strip()
        aadhar    = request.POST.get('aadhar_no', '').strip()
        password  = request.POST.get('password', '')
        confirm   = request.POST.get('confirm_password', '')

        # ── Validations ──
        if len(aadhar) != 12 or not aadhar.isdigit():
            messages.error(request, '❌ Aadhar number must be exactly 12 digits!')
            return render(request, 'registration.html')

        if password != confirm:
            messages.error(request, '❌ Passwords do not match!')
            return render(request, 'registration.html')

        if len(password) < 8:
            messages.error(request, '❌ Password must be at least 8 characters!')
            return render(request, 'registration.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Username already taken!')
            return render(request, 'registration.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, '❌ Email already registered!')
            return render(request, 'registration.html')

        if VoterProfile.objects.filter(aadhar_no=aadhar).exists():
            messages.error(request, '❌ This Aadhar number is already registered!')
            return render(request, 'registration.html')

        # ── Create User (inactive until OTP verified) ──
        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.is_active = False  # Inactive until OTP verified
        user.save()

        # ── Create VoterProfile with OTP ──
        otp = generate_otp()
        VoterProfile.objects.create(
            user=user,
            aadhar_no=aadhar,
            is_verified=False,
            otp=otp,
            otp_created=timezone.now()
        )

        # ── Send OTP Email ──
        try:
            send_otp_email(email, otp, "Registration")
            request.session['verify_email']   = email
            request.session['verify_purpose'] = 'register'
            messages.success(request, f'✅ OTP sent to {email}! Check your inbox.')
            return redirect('verify_otp')
        except Exception as e:
            user.delete()  # Rollback
            messages.error(request, '❌ Email sending failed! Check email settings.')
            return render(request, 'registration.html')

    return render(request, 'registration.html')


# ══════════════════════════════════════════════════════════════
# OTP VERIFICATION — Step 2: Enter OTP
# ══════════════════════════════════════════════════════════════
def verify_otp_view(request):
    email   = request.session.get('verify_email')
    purpose = request.session.get('verify_purpose', 'register')

    if not email:
        messages.error(request, 'Session expired. Please try again.')
        return redirect('login')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()

        # ── Validate OTP length ──
        if len(entered_otp) != 6 or not entered_otp.isdigit():
            messages.error(request, '❌ Please enter a valid 6-digit OTP!')
            return render(request, 'verify_otp.html', {'email': email, 'purpose': purpose})

        try:
            user    = User.objects.get(email=email)
            profile = VoterProfile.objects.get(user=user)
        except (User.DoesNotExist, VoterProfile.DoesNotExist):
            messages.error(request, '❌ User not found!')
            return redirect('register')

        # ── Check OTP expiry ──
        if not profile.is_otp_valid():
            messages.error(request, '❌ OTP expired! Please try again.')
            if purpose == 'register':
                user.delete()
                return redirect('register')
            return redirect('login')

        # ── Check OTP match ──
        if profile.otp != entered_otp:
            messages.error(request, '❌ Wrong OTP! Please try again.')
            return render(request, 'verify_otp.html', {'email': email, 'purpose': purpose})

        # ── OTP Correct — Registration ──
        if purpose == 'register':
            user.is_active   = True
            user.save()
            profile.is_verified = True
            profile.otp         = ''
            profile.save()
            del request.session['verify_email']
            del request.session['verify_purpose']
            messages.success(request, '✅ Email verified! Account created. Please login.')
            return redirect('login')

        # ── OTP Correct — Login ──  ✅ FIX: backend specified kiya
        elif purpose == 'login':
            profile.otp = ''
            profile.save()
            del request.session['verify_email']
            del request.session['verify_purpose']
            user.backend = 'django.contrib.auth.backends.ModelBackend'  # ✅ 500 error fix
            login(request, user)
            messages.success(request, f'✅ Welcome back, {user.username}!')
            return redirect('dashboard')

    return render(request, 'verify_otp.html', {'email': email, 'purpose': purpose})


# ── RESEND OTP ─────────────────────────────────────────────────
def resend_otp_view(request):
    email   = request.session.get('verify_email')
    purpose = request.session.get('verify_purpose', 'register')

    if not email:
        messages.error(request, '❌ Session expired. Please try again.')
        return redirect('login')

    try:
        user    = User.objects.get(email=email)
        profile = VoterProfile.objects.get(user=user)
        otp = generate_otp()
        profile.otp         = otp
        profile.otp_created = timezone.now()
        profile.save()
        send_otp_email(email, otp, purpose.capitalize())
        messages.success(request, f'✅ New OTP sent to {email}!')
    except Exception as e:
        messages.error(request, '❌ Failed to resend OTP. Please try again.')

    return redirect('verify_otp')


# ══════════════════════════════════════════════════════════════
# LOGIN — Step 1: Username + Password
# ══════════════════════════════════════════════════════════════
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # ── Check user exists ──
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, '❌ Invalid username or password!')
            return render(request, 'login.html')

        # ── Check profile verified ──
        try:
            profile = VoterProfile.objects.get(user=user_obj)
            if not profile.is_verified:
                messages.error(request, '❌ Email not verified! Please register again.')
                return render(request, 'login.html')
        except VoterProfile.DoesNotExist:
            messages.error(request, '❌ Voter profile not found!')
            return render(request, 'login.html')

        # ── Authenticate password ──
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, '❌ Invalid username or password!')
            return render(request, 'login.html')

        # ── Send Login OTP ──
        otp = generate_otp()
        profile.otp         = otp
        profile.otp_created = timezone.now()
        profile.save()

        try:
            send_otp_email(user.email, otp, "Login")
            request.session['verify_email']   = user.email
            request.session['verify_purpose'] = 'login'
            messages.success(request, f'✅ OTP sent to {user.email}! Enter to login.')
            return redirect('verify_otp')
        except Exception as e:
            messages.error(request, '❌ OTP email failed! Check email settings.')
            return render(request, 'login.html')

    return render(request, 'login.html')


# ── LOGOUT ─────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.success(request, '👋 Logged out successfully!')
    return redirect('login')


# ── DASHBOARD ──────────────────────────────────────────────────
@login_required(login_url='login')
def dashboard_view(request):
    election    = Election.objects.filter(is_active=True).first()
    candidates  = Candidate.objects.all()
    total_votes = Vote.objects.count()
    user_voted  = Vote.objects.filter(user=request.user).exists()
    user_vote   = Vote.objects.filter(user=request.user).first()
    can_vote    = election and election.is_ongoing() and not user_voted

    try:
        profile = VoterProfile.objects.get(user=request.user)
    except VoterProfile.DoesNotExist:
        profile = None

    return render(request, 'dashboard.html', {
        'candidates'  : candidates,
        'total_votes' : total_votes,
        'user_voted'  : user_voted,
        'user_vote'   : user_vote,
        'election'    : election,
        'can_vote'    : can_vote,
        'time_seconds': election.time_remaining_seconds() if election else 0,
        'profile'     : profile,
    })


# ── VOTE ───────────────────────────────────────────────────────
@login_required(login_url='login')
def vote_view(request):
    if request.method == 'POST':
        election = Election.objects.filter(is_active=True).first()
        if not election or not election.is_ongoing():
            messages.error(request, '❌ Voting is not allowed right now!')
            return redirect('dashboard')

        if Vote.objects.filter(user=request.user).exists():
            messages.error(request, '❌ You have already voted!')
            return redirect('dashboard')

        candidate_id = request.POST.get('candidate_id', '')
        if not candidate_id or not candidate_id.isdigit():
            messages.error(request, '❌ Invalid request!')
            return redirect('dashboard')

        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            messages.error(request, '❌ Candidate not found!')
            return redirect('dashboard')

        Vote.objects.create(user=request.user, candidate=candidate)
        candidate.votes += 1
        candidate.save()
        messages.success(request, f'✅ Vote cast for {candidate.name}!')
        return redirect('results')

    return redirect('dashboard')


# ── RESULTS ────────────────────────────────────────────────────
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


# ── VOTER LIST (Admin only) ────────────────────────────────────
@login_required(login_url='login')
def voter_list_view(request):
    if not request.user.is_staff:
        messages.error(request, '❌ Admin access only!')
        return redirect('dashboard')
    votes = Vote.objects.all().order_by('-timestamp')
    return render(request, 'voter_list.html', {'votes': votes})
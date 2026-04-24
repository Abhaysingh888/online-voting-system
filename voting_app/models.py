from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ================= ELECTION =================
class Election(models.Model):
    title      = models.CharField(max_length=200, default="General Election")
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()
    is_active  = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def has_started(self):
        return timezone.now() >= self.start_time

    def has_ended(self):
        return timezone.now() >= self.end_time

    def is_ongoing(self):
        return self.has_started() and not self.has_ended()

    def time_remaining_seconds(self):
        if self.has_ended():
            return 0
        return max(int((self.end_time - timezone.now()).total_seconds()), 0)

    def status_label(self):
        if not self.has_started():
            return "upcoming"
        if self.is_ongoing():
            return "ongoing"
        return "ended"

    class Meta:
        ordering = ['-start_time']


# ================= CANDIDATE =================
class Candidate(models.Model):
    name   = models.CharField(max_length=200)
    party  = models.CharField(max_length=200)
    image  = models.URLField(blank=True)
    votes  = models.IntegerField(default=0)  # Denormalized count — updated atomically via F()

    def __str__(self):
        return f"{self.name} ({self.party})"

    class Meta:
        ordering = ['-votes']


# ================= VOTER PROFILE =================
class VoterProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    aadhar_no   = models.CharField(max_length=12, unique=True)
    is_verified = models.BooleanField(default=False)
    otp         = models.CharField(max_length=64, blank=True)   # stores SHA-256 hex digest
    otp_created = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} | Aadhar: {self.aadhar_no} | Verified: {self.is_verified}"
    def is_otp_valid(self):
      if not self.otp_created:
        return False

      now = timezone.now()

    # timezone safe handling
      if timezone.is_naive(self.otp_created):
        otp_time = timezone.make_aware(self.otp_created)
      else:
        otp_time = self.otp_created

      return (now - otp_time).total_seconds() < 600
    
        
    
# ================= VOTE =================
class Vote(models.Model):
    """
    OneToOneField on user  →  one voter = one vote, enforced at DB level.
    No election FK needed because the system runs one election at a time.
    Candidate.votes (int) is the authoritative count, updated atomically
    via F() expression in vote_view so no race condition.
    """
    user      = models.OneToOneField(
                    User,
                    on_delete=models.CASCADE,
                    related_name='vote'         # request.user.vote  (single object)
                )
    candidate = models.ForeignKey(
                    Candidate,
                    on_delete=models.CASCADE,
                    related_name='vote_records'  # candidate.vote_records.count()
                )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.candidate.name} at {self.timestamp:%d %b %Y %I:%M %p}"
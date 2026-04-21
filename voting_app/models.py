from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Candidate(models.Model):
    name      = models.CharField(max_length=200)
    party     = models.CharField(max_length=200)
    image     = models.URLField(blank=True)
    votes     = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.party})"

    class Meta:
        ordering = ['-votes']
        
class VoterProfile(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    aadhar_no   = models.CharField(max_length=12, unique=True)  # 12 digit unique
    is_verified = models.BooleanField(default=False)             # Email OTP verified?
    otp         = models.CharField(max_length=6, blank=True)
    otp_created = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} | Aadhar: {self.aadhar_no} | Verified: {self.is_verified}"

    def is_otp_valid(self):
        """OTP 10 minute tak valid rahega"""
        if not self.otp_created:
            return False
        diff = timezone.now() - self.otp_created
        return diff.total_seconds() < 600  # 600 seconds = 10 min

    def masked_aadhar(self):
        """XXXX-XXXX-1234 format"""
        return f"XXXX-XXXX-{self.aadhar_no[-4:]}"


class Vote(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='vote_records')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'candidate')  # One vote per user per candidate

    def __str__(self):
        return f"{self.user.username} → {self.candidate.name} at {self.timestamp}"
    
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
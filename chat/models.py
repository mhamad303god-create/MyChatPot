from django.db import models


class Chat(models.Model):
    title = models.CharField(max_length=200, default="محادثة جديدة")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Message(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("ai", "AI"),
    )
    chat = models.ForeignKey(Chat, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    text = models.TextField(blank=True, null=True) # Allow empty text if image is present
    image = models.ImageField(upload_to="chat_images/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        txt = self.text[:50] if self.text else "[Image]"
        return f"{self.role}: {txt}..."
    
    class Meta:
        ordering = ["created_at"]

        
        
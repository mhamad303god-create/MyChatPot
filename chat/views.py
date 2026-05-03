from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Chat, Message

import os
import json
import google.generativeai as genai 

# =========================
# Gemini Client Configuration
# =========================
api_key = os.getenv("GEMINI_API_KEY")

def get_best_model():
    """وظيفة للبحث عن الموديل المتاح في حساب المستخدم لتجنب خطأ 404"""
    if not api_key:
        return None
    
    genai.configure(api_key=api_key)
    
    # قائمة الموديلات التي نفضل استخدامها بالترتيب
    preferred_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    try:
        # جلب قائمة الموديلات المتاحة لهذا المفتاح (API Key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        for model_name in preferred_models:
            # التحقق من الاسم المختصر أو الكامل (models/name)
            full_name = f"models/{model_name}"
            if full_name in available_models or model_name in available_models:
                return genai.GenerativeModel(model_name)
        
        # إذا لم يجد المفضل، يأخذ أول موديل متاح يدعم توليد المحتوى
        if available_models:
            return genai.GenerativeModel(available_models[0])
    except Exception:
        # في حال فشل الاتصال، نستخدم المسمى الافتراضي كمحاولة أخيرة
        return genai.GenerativeModel('gemini-1.5-flash')
    
    return None

# تهيئة الموديل عند تشغيل السيرفر
model = get_best_model()

# =========================
# INDEX
# =========================
@ensure_csrf_cookie
def index(request):
    return render(request, "chat/index.html")

# =========================
# CHATS MANAGEMENT
# =========================
@require_http_methods(["GET"])
def get_chats(request):
    chats = Chat.objects.all().order_by("-created_at")
    return JsonResponse([{"id": c.id, "title": c.title} for c in chats], safe=False)

@require_http_methods(["POST"])
def create_chat(request):
    chat = Chat.objects.create(title="محادثة جديدة")
    return JsonResponse({"id": chat.id, "title": chat.title})

@require_http_methods(["GET"])
def get_chat_details(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    return JsonResponse({
        "id": chat.id,
        "title": chat.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "text": m.text,
                "image": m.image.url if m.image else None
            }
            for m in chat.messages.all()
        ]
    })

@require_http_methods(["POST"])
def rename_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    try:
        data = json.loads(request.body)
        title = data.get("title", "").strip()
        if not title:
            return JsonResponse({"error": "title required"}, status=400)
        chat.title = title
        chat.save()
        return JsonResponse({"id": chat.id, "title": chat.title})
    except:
        return JsonResponse({"error": "invalid data"}, status=400)

@require_http_methods(["DELETE"])
def delete_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    chat.delete()
    return JsonResponse({"message": "deleted"})

# =========================
# SEND MESSAGE (Gemini Streaming)
# =========================
@require_http_methods(["POST"])
def send_message(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)

    # معالجة مشكلة RawPostDataException
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
    except Exception:
        return JsonResponse({"error": "Invalid request body"}, status=400)

    text = data.get("text", "")
    if not text:
        return JsonResponse({"error": "empty message"}, status=400)

    # حفظ رسالة المستخدم
    user_msg = Message.objects.create(chat=chat, role="user", text=text)

    # تحديث العنوان التلقائي
    if chat.title == "محادثة جديدة":
        chat.title = text[:30]
        chat.save()

    def stream():
        # استخدام الموديل العالمي الذي تم تهيئته
        global model
        if model is None:
            model = get_best_model() # محاولة ثانية للتهيئة
            
        if model is None:
            yield f"data: {json.dumps({'error': 'Gemini API not configured correctly'})}\n\n"
            return

        full_response_text = ""
        try:
            # بناء التاريخ
            history = []
            past_messages = chat.messages.exclude(id=user_msg.id).order_by('created_at')
            
            for m in past_messages:
                history.append({
                    "role": "user" if m.role == "user" else "model",
                    "parts": [m.text]
                })

            # بدء الدردشة
            chat_session = model.start_chat(history=history)
            response = chat_session.send_message(text, stream=True)

            for chunk in response:
                try:
                    if chunk.text:
                        full_response_text += chunk.text
                        yield f"data: {json.dumps({'chunk': chunk.text}, ensure_ascii=False)}\n\n"
                except:
                    continue

            # حفظ رد الـ AI
            if full_response_text.strip():
                Message.objects.create(chat=chat, role="ai", text=full_response_text)

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingHttpResponse(stream(), content_type="text/event-stream")


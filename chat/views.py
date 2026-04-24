from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Chat, Message
import os
import json
import google.generativeai as genai

# جلب المفتاح من نظام التشغيل (الموجود في Render)
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    print("Error: GEMINI_API_KEY not found in environment variables")

_MODEL_CACHE = {"name": None}
_MODEL_FALLBACKS = (
    "gemini-2.0-flash",
    "gemini-1.5-flash",
)

def _get_env_list(name):
    value = os.getenv(name, "").strip()
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]

def _normalize_model_name(name):
    if not name: return name
    return name.split("/", 1)[1] if name.startswith("models/") else name

def _resolve_model(client, refresh=False, exclude=None):
    for m in _get_env_list("GEMINI_MODEL"):
        name = _normalize_model_name(m)
        if name != exclude: return name
    
    cached = _MODEL_CACHE["name"]
    if cached and not refresh and cached != exclude: return cached

    try:
        # ملاحظة: list_models تتبع مكتبة generativeai القديمة
        for model in genai.list_models():
            if "generateContent" in model.supported_generation_methods:
                name = _normalize_model_name(model.name)
                if exclude and name == exclude: continue
                _MODEL_CACHE["name"] = name
                return name
    except: pass

    for m in _MODEL_FALLBACKS:
        if m != exclude: return m
    return exclude or "gemini-1.5-flash"

def _get_client(api_version=None):
    # تم التصحيح هنا: نستخدم os.getenv أو api_key المباشر بدل settings
    from google import genai as genai_new
    current_key = os.getenv("GEMINI_API_KEY")
    version = _get_env_list("GEMINI_API_VERSION")
    
    if version:
        return genai_new.Client(api_key=current_key, api_version=version[0])
    if api_version:
        return genai_new.Client(api_key=current_key, api_version=api_version)
    return genai_new.Client(api_key=current_key)

def _create_chat_session(client, model, history, sys_inst, temperature):
    from google.genai import types
    return client.chats.create(
        model=model,
        history=history,
        config=types.GenerateContentConfig(
            system_instruction=sys_inst,
            temperature=temperature,
        ),
    )

def _is_model_not_found(err):
    msg = str(err).lower()
    return "not found" in msg or "not supported for generatecontent" in msg

def _should_try_v1(err):
    msg = str(err).lower()
    return "v1beta" in msg or "api version v1beta" in msg

@ensure_csrf_cookie
def index(request):
    return render(request, "chat/index.html")

@require_http_methods(["GET"])
def get_chats(request):
    chats = Chat.objects.all().order_by("-created_at")
    data = [{"id": c.id, "title": c.title} for c in chats]
    return JsonResponse(data, safe=False)

@require_http_methods(["POST"])
def create_chat(request):
    chat = Chat.objects.create(title="محادثة جديدة")
    return JsonResponse({"id": chat.id, "title": chat.title})

@require_http_methods(["GET"])
def get_chat_details(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    messages = chat.messages.all().order_by("created_at")
    data = {
        "id": chat.id,
        "title": chat.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "text": m.text,
                "image_url": m.image.url if m.image else None
            } for m in messages
        ],
    }
    return JsonResponse(data)

@require_http_methods(["POST"])
def send_message(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    
    try:
        user_text = ""
        image_file = None
        system_instruction = None
        temperature = 0.7

        if request.content_type == "application/json":
            data = json.loads(request.body)
            user_text = data.get("text", "")
            system_instruction = data.get("system_instruction")
            temperature = float(data.get("temperature", 0.7))
        else:
            user_text = request.POST.get("text", "")
            image_file = request.FILES.get("image")
            system_instruction = request.POST.get("system_instruction")
            temperature = float(request.POST.get("temperature", 0.7))

        if not user_text and not image_file:
            return JsonResponse({"error": "No text or image provided"}, status=400)

        msg = Message.objects.create(chat=chat, role="user", text=user_text, image=image_file)

        # تحديث العنوان تلقائياً
        if chat.title == "محادثة جديدة":
            chat.title = user_text[:30] + "..." if len(user_text) > 30 else user_text
            chat.save()

    except Exception as e:
         return JsonResponse({"error": str(e)}, status=400)

    def event_stream():
        full_ai_text = ""
        try:
            from google.genai import types
            previous_messages = chat.messages.exclude(id=msg.id).order_by("created_at")
            history = []
            for m in previous_messages:
                role = "user" if m.role == "user" else "model"
                history.append(types.Content(role=role, parts=[types.Part(text=m.text or "[صورة]")]))

            sys_inst = system_instruction or "أنت خبير ذكاء اصطناعي محترف. أجب دائماً بالعربية."

            client = _get_client()
            model_name = _resolve_model(client)
            
            chat_session = _create_chat_session(client, model_name, history, sys_inst, temperature)

            message_parts = []
            if msg.text: message_parts.append(types.Part(text=msg.text))
            if msg.image:
                if msg.image.closed: msg.image.open()
                message_parts.append(types.Part.from_bytes(data=msg.image.read(), mime_type='image/jpeg'))

            response = chat_session.send_message_stream(message_parts)

            for chunk in response:
                if chunk.text:
                    full_ai_text += chunk.text
                    yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
            
            yield f"data: {json.dumps({'done': True, 'chat_id': chat.id})}\n\n"
            Message.objects.create(chat=chat, role="ai", text=full_ai_text)

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
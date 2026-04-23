from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Chat, Message
import os
import json


_MODEL_CACHE = {"name": None}
_MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
)


def _get_env_list(name):
    value = os.getenv(name, "").strip()
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _normalize_model_name(name):
    if not name:
        return name
    return name.split("/", 1)[1] if name.startswith("models/") else name


def _resolve_model(client, refresh=False, exclude=None):
    for m in _get_env_list("GEMINI_MODEL"):
        name = _normalize_model_name(m)
        if name != exclude:
            return name

    cached = _MODEL_CACHE["name"]
    if cached and not refresh and cached != exclude:
        return cached

    try:
        for model in client.models.list():
            methods = getattr(model, "supported_generation_methods", None) or []
            if "generateContent" in methods:
                name = _normalize_model_name(model.name)
                if exclude and name == exclude:
                    continue
                _MODEL_CACHE["name"] = name
                return name
    except Exception:
        pass

    for m in _MODEL_FALLBACKS:
        if m != exclude:
            return m
    return exclude or "gemini-1.5-flash"


def _get_client(api_version=None):
    from google import genai
    version = _get_env_list("GEMINI_API_VERSION")
    if version:
        return genai.Client(api_key=settings.GEMINI_API_KEY, api_version=version[0])
    if api_version:
        return genai.Client(api_key=settings.GEMINI_API_KEY, api_version=api_version)
    return genai.Client(api_key=settings.GEMINI_API_KEY)


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
    chat = Chat.objects.create()
    return JsonResponse({"id": chat.id, "title": chat.title})


@require_http_methods(["GET"])
def get_chat_details(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    messages = chat.messages.all()
    data = {
        "id": chat.id,
        "title": chat.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "text": m.text,
                "image_url": m.image.url if m.image else None
            }
            for m in messages
        ],
    }
    return JsonResponse(data)


@require_http_methods(["POST"])
def rename_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    try:
        data = json.loads(request.body)
        new_title = data.get("title")
        if new_title:
            chat.title = new_title
            chat.save()
            return JsonResponse({"status": "ok", "title": chat.title})
    except:
        pass
    return JsonResponse({"status": "error"}, status=400)


@require_http_methods(["DELETE"])
def delete_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    chat.delete()
    return JsonResponse({"status": "ok"})


@require_http_methods(["POST"])
def send_message(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    
    # 1. Parse Request
    try:
        user_text = ""
        image_file = None
        system_instruction = None
        temperature = 0.7

        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                user_text = data.get("text", "")
                system_instruction = data.get("system_instruction")
                temperature = float(data.get("temperature", 0.7))
            except:
                pass
        else:
            user_text = request.POST.get("text", "")
            image_file = request.FILES.get("image")
            system_instruction = request.POST.get("system_instruction")
            try:
                temperature = float(request.POST.get("temperature", 0.7))
            except:
                pass

        if not user_text and not image_file:
            return JsonResponse({"error": "No text or image provided"}, status=400)

        # 2. Check for Edit Mode
        edit_message_id = request.POST.get("edit_message_id")
        msg = None
        
        if edit_message_id:
             # Edit Logic: Get message, update text, delete subsequent messages
             msg = get_object_or_404(Message, id=edit_message_id, chat=chat, role="user")
             msg.text = user_text
             if image_file:
                 msg.image = image_file
             msg.save()
             
             # Delete all messages *after* this edited message (timeline reset)
             chat.messages.filter(created_at__gt=msg.created_at).delete()
        else:
             # Normal Send: Create new message
             msg = Message.objects.create(chat=chat, role="user", text=user_text, image=image_file)

        # 3. Auto-title
        if not edit_message_id and (chat.messages.filter(role="user").count() == 1 or chat.title == "محادثة جديدة"):
            title_text = user_text if user_text else "Conversation with Image"
            new_title = title_text[:30] + "..." if len(title_text) > 30 else title_text
            chat.title = new_title
            chat.save()

    except Exception as e:
         return JsonResponse({"error": str(e)}, status=400)

    # 4. Streaming Generator Function
    def event_stream():
        full_ai_text = ""
        try:
            from google.genai import types

            # Build History
            # IMPORTANT: For edit, we exclude the *current* message (msg) from history
            # because we send it as the final prompt.
            previous_messages = chat.messages.exclude(id=msg.id).order_by("created_at")
            history = []
            for m in previous_messages:
                role = "user" if m.role == "user" else "model"
                part_text = m.text if m.text else "[Image Sent]"
                history.append(types.Content(role=role, parts=[types.Part(text=part_text)]))

            # System Instruction
            sys_inst = system_instruction
            if not sys_inst:
                sys_inst = """أنت خبير ذكاء اصطناعي محترف في تطوير الويب (Web Development).
اللغة: يجب أن تجيب **دائمًا** باللغة العربية الفصحى، حتى لو كان السؤال بلغة أخرى.
الأسلوب: مباشر، دقيق، واحترافي.
الأكواد: استخدم كتل التعليمات البرمجية (Code Blocks) وشرحها بوضوح.
التنسيق: استخدم Markdown لتنسيق الإجابة بشكل جميل ومنظم."""

            # Config
            client = _get_client()
            model = _resolve_model(client)
            try:
                chat_session = _create_chat_session(
                    client=client,
                    model=model,
                    history=history,
                    sys_inst=sys_inst,
                    temperature=temperature,
                )
            except Exception as e:
                if _is_model_not_found(e):
                    alt_client = client
                    if _should_try_v1(e):
                        alt_client = _get_client(api_version="v1")
                    alt_model = _resolve_model(alt_client, refresh=True, exclude=model)
                    chat_session = _create_chat_session(
                        client=alt_client,
                        model=alt_model,
                        history=history,
                        sys_inst=sys_inst,
                        temperature=temperature,
                    )
                else:
                    raise

            # Current Message
            message_parts = []
            if msg.text:
                message_parts.append(types.Part(text=msg.text))
            
            if msg.image:
                # Re-open file for reading if needed
                if msg.image.closed:
                    msg.image.open()
                image_bytes = msg.image.read()
                # Determine mime_type (fallback to jpeg if unknown)
                mime = msg.image.file.content_type if hasattr(msg.image.file, 'content_type') else 'image/jpeg'
                message_parts.append(types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime
                ))

            # Send with send_message_stream for streaming response
            response = chat_session.send_message_stream(message_parts)

            for chunk in response:
                if chunk.text:
                    text_chunk = chunk.text
                    full_ai_text += text_chunk
                    # SSE format: data: <content>\n\n
                    payload = json.dumps({"chunk": text_chunk})
                    yield f"data: {payload}\n\n"
            
            # End of stream - Send Meta Info
            meta = json.dumps({
                "done": True, 
                "chat_title": chat.title,
                "chat_id": chat.id,
                "user_message_id": msg.id
            })
            yield f"data: {meta}\n\n"

            # 5. Save AI Message to DB
            Message.objects.create(chat=chat, role="ai", text=full_ai_text)

        except Exception as e:
            error_msg = json.dumps({"error": str(e)})
            yield f"data: {error_msg}\n\n"
            # Attempt to save partial
            if full_ai_text:
                 Message.objects.create(chat=chat, role="ai", text=full_ai_text + "\n[System Error: Interrupted]")

    from django.http import StreamingHttpResponse
    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no" # For Nginx
    return response

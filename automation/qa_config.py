from __future__ import annotations


SEVERITY_BLOCKER = "BLOCKER"
SEVERITY_WARNING = "WARNING"

REQUIRED_HEADERS = [
    "Asset Type",
    "Campaigns",
    "Partner CF:Global Autofill Tagging",
    "Message Name",
    "Channel",
    "Media Title",
    "Partner CF:Language",
    "Partner CF:Language_GSM",
    "Partner CF:Post Media Type",
    "IMAGE-NAME",
    "Asset link",
    "Asset Name",
    "Message",
    "HASHTAGS",
    "Character count",
    "Image or video copy",
    "Alt-Text",
    "Partner CF:Global Social | Corp to Field - Content Drop Name",
]

REQUIRED_VALUE_COLUMNS = [
    "Asset Type",
    "Campaigns",
    "Partner CF:Global Autofill Tagging",
    "Message Name",
    "Message",
    "Channel",
    "Media Title",
    "Partner CF:Language",
    "Asset Name",
    "Character count",
    "Partner CF:Global Social | Corp to Field - Content Drop Name",
]

FIXED_VALUE_RULES = {
    "Asset Type": "Post",
    "Campaigns": "Social: Broadcast",
}

ALLOWED_CHANNELS = {"X", "Facebook", "Instagram", "LinkedIn", "Threads", "TikTok"}
INVALID_CHANNEL_WARNING_MAP = {"Twitter", "Twitter/X", "X/Twitter"}

TEXT_ONLY_VALUE = "Text-only"

IMAGE_TYPES_FOR_ALT_TEXT = {
    "Image",
    "Photography",
    "Image/Photography/Carousel",
    "Carousel",
}

MEDIA_EXTENSION_RULES = {
    "LinkedIn Document Ad": {".pdf"},
    "GIF": {".gif"},
    "Video": {".mp4"},
    "Image": {".png", ".jpg", ".jpeg"},
    "Photography": {".png", ".jpg", ".jpeg"},
    "Carousel": {".png", ".jpg", ".jpeg"},
    "Image/Photography/Carousel": {".png", ".jpg", ".jpeg"},
}

AUTOFILL_DYNAMIC_EXCLUDE = {
    "Message",
    "HASHTAGS",
    "Character count",
    "Image or Video copy",
    "Alt-Text",
    "IMAGE-NAME",
    "Asset link",
    "Asset Name",
    "Message Name",
    "Source Row Number",
}

HEADER_ALIASES = {
    "partner cf:global social | corp to field - content drop name":
        "Partner CF:Global Social | Corp to Field - Content Drop Name",
    "image or video copy": "Image or Video copy",
    "image-name": "IMAGE-NAME",
    "hashtags": "HASHTAGS",
    "alt-text": "Alt-Text",
}
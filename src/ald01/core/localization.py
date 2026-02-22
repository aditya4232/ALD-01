"""
ALD-01 Localization System
Multi-language support with Hindi, Hinglish, and English.
Provides translatable dialogues, greetings, error messages, and UI strings.
"""

import os
import json
import random
import logging
from typing import Any, Dict, List, Optional

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.localization")


# ──────────────────────────────────────────────────────────────
# Language Packs
# ──────────────────────────────────────────────────────────────

LANGUAGES: Dict[str, Dict[str, Any]] = {
    "en": {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "icon": "🇬🇧",
        "strings": {
            # Greetings
            "greeting_morning": "Good morning! How can I help you today?",
            "greeting_afternoon": "Good afternoon! What are we working on?",
            "greeting_evening": "Good evening! Ready when you are.",
            "greeting_default": "Hey! What can I do for you?",
            "greeting_return": "Welcome back! What's on your mind?",

            # Status
            "status_thinking": "Thinking...",
            "status_processing": "Processing your request...",
            "status_done": "Done!",
            "status_error": "Something went wrong. Let me try again.",
            "status_ready": "Ready to help.",

            # Commands
            "cmd_exit": "Goodbye! See you later.",
            "cmd_clear": "Conversation cleared.",
            "cmd_help": "Here are the available commands:",

            # Responses
            "resp_dont_understand": "I'm not sure I understand. Could you rephrase?",
            "resp_working_on_it": "Working on it...",
            "resp_completed": "All done! Here's what I've got:",
            "resp_error_recovery": "I hit an issue, but I'm recovering automatically.",
            "resp_mode_switched": "Mode switched to {mode}. I'm now focused on {focus}.",
            "resp_no_provider": "No AI providers available. Run 'ald-01 doctor' to diagnose.",

            # Notifications
            "notif_task_complete": "Background task completed: {task}",
            "notif_backup_done": "Backup completed successfully.",
            "notif_health_warning": "Health check found issues. Run 'ald-01 doctor'.",

            # Doctor
            "doctor_checking": "Running diagnostics...",
            "doctor_all_good": "All systems operational! Everything looks great.",
            "doctor_issues": "Found {count} issue(s). Here's what needs attention:",
            "doctor_fixed": "Fixed {count} issue(s) automatically.",

            # Onboarding
            "onboard_welcome": "Welcome to ALD-01! Let's get you set up.",
            "onboard_complete": "Setup complete! You're ready to go.",

            # Fun dialogues
            "fun_motivational": [
                "Let's build something amazing!",
                "I'm ready to code. Are you?",
                "Another day, another bug to squash!",
                "Let's make today productive!",
            ],
        },
    },
    "hi": {
        "code": "hi",
        "name": "Hindi",
        "native_name": "हिन्दी",
        "icon": "🇮🇳",
        "strings": {
            "greeting_morning": "सुप्रभात! आज मैं आपकी कैसे मदद कर सकता हूं?",
            "greeting_afternoon": "नमस्ते! आज क्या काम कर रहे हैं?",
            "greeting_evening": "शुभ संध्या! बताइए क्या करना है?",
            "greeting_default": "नमस्ते! बताइए मैं क्या मदद कर सकता हूं?",
            "greeting_return": "वापसी का स्वागत है! क्या चल रहा है?",

            "status_thinking": "सोच रहा हूं...",
            "status_processing": "आपकी request पर काम कर रहा हूं...",
            "status_done": "हो गया!",
            "status_error": "कुछ गड़बड़ हो गई। दोबारा try करता हूं।",
            "status_ready": "मदद के लिए तैयार।",

            "cmd_exit": "अलविदा! फिर मिलेंगे।",
            "cmd_clear": "बातचीत साफ कर दी।",
            "cmd_help": "यहां उपलब्ध commands हैं:",

            "resp_dont_understand": "मुझे समझ नहीं आया। क्या आप दोबारा बता सकते हैं?",
            "resp_working_on_it": "काम कर रहा हूं...",
            "resp_completed": "सब हो गया! यह रहा:",
            "resp_error_recovery": "एक समस्या आई, लेकिन मैं ठीक कर रहा हूं।",
            "resp_mode_switched": "Mode बदलकर {mode} कर दिया। अब {focus} पर ध्यान है।",
            "resp_no_provider": "कोई AI provider उपलब्ध नहीं। 'ald-01 doctor' चलाएं।",

            "notif_task_complete": "Background task पूरा हो गया: {task}",
            "notif_backup_done": "Backup सफलतापूर्वक हो गया।",
            "notif_health_warning": "Health check में issues मिलीं। 'ald-01 doctor' चलाएं।",

            "doctor_checking": "जांच कर रहा हूं...",
            "doctor_all_good": "सब सिस्टम ठीक काम कर रहे हैं!",
            "doctor_issues": "{count} समस्या(एं) मिलीं। ध्यान दीजिए:",
            "doctor_fixed": "{count} समस्या(एं) अपने आप ठीक कर दीं।",

            "onboard_welcome": "ALD-01 में स्वागत है! चलिए setup करते हैं।",
            "onboard_complete": "Setup पूरा! अब शुरू करें।",

            "fun_motivational": [
                "चलो कुछ बढ़िया बनाते हैं!",
                "आज कुछ नया code करें?",
                "एक और दिन, एक और bug fix!",
                "आज productive दिन बनाते हैं!",
            ],
        },
    },
    "hinglish": {
        "code": "hinglish",
        "name": "Hinglish",
        "native_name": "Hinglish",
        "icon": "🇮🇳",
        "strings": {
            "greeting_morning": "Good morning bhai! Aaj kya karna hai?",
            "greeting_afternoon": "Hello! Kya chal raha hai?",
            "greeting_evening": "Good evening! Batao kya help chahiye?",
            "greeting_default": "Hey! Kya kar sakte hain aaj?",
            "greeting_return": "Welcome back! Kya plan hai?",

            "status_thinking": "Soch raha hoon...",
            "status_processing": "Tumhari request pe kaam kar raha hoon...",
            "status_done": "Ho gaya!",
            "status_error": "Kuch gadbad ho gayi. Phir se try karta hoon.",
            "status_ready": "Ready hoon boss!",

            "cmd_exit": "Bye bye! Phir milte hain!",
            "cmd_clear": "Chat clear kar diya.",
            "cmd_help": "Ye commands available hain:",

            "resp_dont_understand": "Samajh nahi aaya. Thoda aur explain karo?",
            "resp_working_on_it": "Kaam kar raha hoon...",
            "resp_completed": "Done! Ye raha output:",
            "resp_error_recovery": "Ek problem aayi thi, lekin fix kar diya apne aap.",
            "resp_mode_switched": "Mode change: {mode}. Ab {focus} pe focus hai.",
            "resp_no_provider": "Koi AI provider nahi mila. 'ald-01 doctor' run karo.",

            "notif_task_complete": "Background task complete ho gaya: {task}",
            "notif_backup_done": "Backup ho gaya successfully!",
            "notif_health_warning": "Kuch issues mili. 'ald-01 doctor' check karo.",

            "doctor_checking": "Check kar raha hoon...",
            "doctor_all_good": "Sab sahi chal raha hai! 🎉",
            "doctor_issues": "{count} issue(s) mili. Dekho:",
            "doctor_fixed": "{count} issues apne aap fix kar di!",

            "onboard_welcome": "ALD-01 mein welcome! Setup karte hain.",
            "onboard_complete": "Setup done! Ab shuru karo!",

            "fun_motivational": [
                "Chalo kuch zabardast banate hain!",
                "Coding ka time hai boss!",
                "Aaj bugs ko maaro!",
                "Productive day banate hain!",
                "Tera ALD hai na, tension mat le!",
            ],
        },
    },
}


class LocalizationManager:
    """
    Multi-language support for ALD-01.
    Handles string lookup, language switching, and time-based greetings.
    """

    def __init__(self):
        self._current_lang = "en"
        self._custom_strings: Dict[str, Dict[str, str]] = {}
        self._persistence_path = os.path.join(CONFIG_DIR, "language.json")
        self._load()

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang_code: str) -> bool:
        """Set the active language."""
        lang_code = lang_code.lower().strip()
        if lang_code in LANGUAGES:
            self._current_lang = lang_code
            self._save()
            return True
        return False

    def get_string(self, key: str, **kwargs) -> str:
        """Get a localized string by key."""
        # Check custom overrides first
        custom = self._custom_strings.get(self._current_lang, {})
        if key in custom:
            return custom[key].format(**kwargs) if kwargs else custom[key]

        # Check language pack
        lang_data = LANGUAGES.get(self._current_lang, LANGUAGES["en"])
        strings = lang_data.get("strings", {})

        if key in strings:
            value = strings[key]
            if isinstance(value, list):
                value = random.choice(value)
            return value.format(**kwargs) if kwargs else value

        # Fallback to English
        en_strings = LANGUAGES["en"]["strings"]
        if key in en_strings:
            value = en_strings[key]
            if isinstance(value, list):
                value = random.choice(value)
            return value.format(**kwargs) if kwargs else value

        return key

    def get_greeting(self) -> str:
        """Get a time-appropriate greeting."""
        import time as _time
        hour = _time.localtime().tm_hour
        if 5 <= hour < 12:
            return self.get_string("greeting_morning")
        elif 12 <= hour < 17:
            return self.get_string("greeting_afternoon")
        elif 17 <= hour < 22:
            return self.get_string("greeting_evening")
        return self.get_string("greeting_default")

    def get_motivational(self) -> str:
        """Get a random motivational dialogue."""
        return self.get_string("fun_motivational")

    def list_languages(self) -> List[Dict[str, str]]:
        """List available languages."""
        return [
            {
                "code": code,
                "name": data["name"],
                "native_name": data["native_name"],
                "icon": data["icon"],
                "active": code == self._current_lang,
            }
            for code, data in LANGUAGES.items()
        ]

    def add_custom_string(self, lang: str, key: str, value: str) -> None:
        """Add or override a string."""
        if lang not in self._custom_strings:
            self._custom_strings[lang] = {}
        self._custom_strings[lang][key] = value
        self._save()

    def _save(self) -> None:
        try:
            data = {
                "language": self._current_lang,
                "custom_strings": self._custom_strings,
            }
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save language: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._current_lang = data.get("language", "en")
                self._custom_strings = data.get("custom_strings", {})
        except Exception:
            self._current_lang = "en"


_localization: Optional[LocalizationManager] = None

def get_localization() -> LocalizationManager:
    global _localization
    if _localization is None:
        _localization = LocalizationManager()
    return _localization

# Convenience function
def t(key: str, **kwargs) -> str:
    """Quick translate function."""
    return get_localization().get_string(key, **kwargs)

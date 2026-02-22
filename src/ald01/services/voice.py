"""
ALD-01 Voice Service
Optional text-to-speech capability using free offline and online engines.
Supports: pyttsx3 (offline), edge-tts (free Microsoft TTS), or system TTS.
"""

import os
import sys
import asyncio
import logging
import platform
import tempfile
from typing import Optional

logger = logging.getLogger("ald01.voice")


class VoiceService:
    """
    Text-to-Speech service for ALD-01.
    Falls back through engines: edge-tts → pyttsx3 → system TTS → silent.
    All engines are free. Voice is entirely optional.
    """

    def __init__(self):
        self.enabled = False
        self.engine_name = "none"
        self._pyttsx_engine = None
        self.voice_id: Optional[str] = None
        self.rate = 175  # words per minute
        self.volume = 0.9

    async def initialize(self) -> bool:
        """Detect and initialize the best available TTS engine."""
        # Try edge-tts first (high quality, free Microsoft TTS)
        if await self._try_edge_tts():
            self.engine_name = "edge-tts"
            self.enabled = True
            logger.info("Voice initialized: edge-tts (Microsoft Neural TTS)")
            return True

        # Try pyttsx3 (offline, works everywhere)
        if self._try_pyttsx3():
            self.engine_name = "pyttsx3"
            self.enabled = True
            logger.info("Voice initialized: pyttsx3 (offline)")
            return True

        # Try system TTS
        if self._try_system_tts():
            self.engine_name = "system"
            self.enabled = True
            logger.info("Voice initialized: system TTS")
            return True

        logger.info("Voice: No TTS engine available. Voice disabled.")
        return False

    async def speak(self, text: str) -> bool:
        """Speak the given text. Returns True if successful."""
        if not self.enabled:
            return False

        try:
            if self.engine_name == "edge-tts":
                return await self._speak_edge_tts(text)
            elif self.engine_name == "pyttsx3":
                return self._speak_pyttsx3(text)
            elif self.engine_name == "system":
                return await self._speak_system(text)
        except Exception as e:
            logger.error(f"Voice error: {e}")
        return False

    async def speak_to_file(self, text: str, output_path: str) -> bool:
        """Generate speech and save to audio file."""
        if not self.enabled:
            return False

        try:
            if self.engine_name == "edge-tts":
                return await self._save_edge_tts(text, output_path)
            elif self.engine_name == "pyttsx3":
                return self._save_pyttsx3(text, output_path)
        except Exception as e:
            logger.error(f"Voice save error: {e}")
        return False

    # ──────────────────────────────────────────────────────────
    # Edge TTS (Free Microsoft Neural Voices)
    # ──────────────────────────────────────────────────────────

    async def _try_edge_tts(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    async def _speak_edge_tts(self, text: str) -> bool:
        try:
            import edge_tts
            voice = self.voice_id or "en-US-AriaNeural"
            communicate = edge_tts.Communicate(text, voice)

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name

            await communicate.save(tmp_path)
            await self._play_audio(tmp_path)
            os.unlink(tmp_path)
            return True
        except Exception as e:
            logger.error(f"edge-tts speak error: {e}")
            return False

    async def _save_edge_tts(self, text: str, output_path: str) -> bool:
        try:
            import edge_tts
            voice = self.voice_id or "en-US-AriaNeural"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return True
        except Exception as e:
            logger.error(f"edge-tts save error: {e}")
            return False

    # ──────────────────────────────────────────────────────────
    # pyttsx3 (Offline)
    # ──────────────────────────────────────────────────────────

    def _try_pyttsx3(self) -> bool:
        try:
            import pyttsx3
            self._pyttsx_engine = pyttsx3.init()
            self._pyttsx_engine.setProperty("rate", self.rate)
            self._pyttsx_engine.setProperty("volume", self.volume)
            return True
        except Exception:
            return False

    def _speak_pyttsx3(self, text: str) -> bool:
        try:
            if self._pyttsx_engine is None:
                import pyttsx3
                self._pyttsx_engine = pyttsx3.init()
            self._pyttsx_engine.say(text)
            self._pyttsx_engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}")
            return False

    def _save_pyttsx3(self, text: str, output_path: str) -> bool:
        try:
            if self._pyttsx_engine is None:
                import pyttsx3
                self._pyttsx_engine = pyttsx3.init()
            self._pyttsx_engine.save_to_file(text, output_path)
            self._pyttsx_engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"pyttsx3 save error: {e}")
            return False

    # ──────────────────────────────────────────────────────────
    # System TTS (OS-native)
    # ──────────────────────────────────────────────────────────

    def _try_system_tts(self) -> bool:
        system = platform.system()
        if system == "Windows":
            return True  # PowerShell has built-in TTS
        elif system == "Darwin":
            return True  # macOS has 'say' command
        elif system == "Linux":
            # Check for espeak
            return os.system("which espeak > /dev/null 2>&1") == 0
        return False

    async def _speak_system(self, text: str) -> bool:
        system = platform.system()
        # Sanitize text for shell safety
        safe_text = text.replace('"', '\\"').replace("'", "\\'")[:500]

        try:
            if system == "Windows":
                cmd = f'powershell -Command "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak(\'{safe_text}\')"'
            elif system == "Darwin":
                cmd = f'say "{safe_text}"'
            elif system == "Linux":
                cmd = f'espeak "{safe_text}"'
            else:
                return False

            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            return True
        except Exception as e:
            logger.error(f"System TTS error: {e}")
            return False

    # ──────────────────────────────────────────────────────────
    # Audio Playback
    # ──────────────────────────────────────────────────────────

    async def _play_audio(self, path: str) -> None:
        """Play an audio file using system tools."""
        system = platform.system()
        try:
            if system == "Windows":
                cmd = f'powershell -Command "(New-Object Media.SoundPlayer \'{path}\').PlaySync()"'
                # For MP3, use wmplayer
                if path.endswith(".mp3"):
                    cmd = f'powershell -Command "Add-Type -AssemblyName PresentationCore; $p = New-Object System.Windows.Media.MediaPlayer; $p.Open([Uri]\'{path}\'); $p.Play(); Start-Sleep -Seconds 10"'
            elif system == "Darwin":
                cmd = f"afplay {path}"
            else:
                cmd = f"mpv --no-video {path} 2>/dev/null || ffplay -nodisp -autoexit {path} 2>/dev/null || aplay {path}"

            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await asyncio.wait_for(proc.wait(), timeout=30)
        except Exception as e:
            logger.debug(f"Audio playback failed: {e}")

    # ──────────────────────────────────────────────────────────
    # Voice Listing
    # ──────────────────────────────────────────────────────────

    async def list_voices(self) -> list:
        """List available voices for the current engine."""
        voices = []
        if self.engine_name == "edge-tts":
            try:
                import edge_tts
                voice_list = await edge_tts.list_voices()
                for v in voice_list:
                    if v.get("Locale", "").startswith("en"):
                        voices.append({
                            "id": v["ShortName"],
                            "name": v["FriendlyName"],
                            "locale": v["Locale"],
                            "gender": v.get("Gender", ""),
                        })
            except Exception:
                pass
        elif self.engine_name == "pyttsx3" and self._pyttsx_engine:
            try:
                for v in self._pyttsx_engine.getProperty("voices"):
                    voices.append({
                        "id": v.id,
                        "name": v.name,
                        "locale": getattr(v, "languages", [""])[0] if hasattr(v, "languages") else "",
                    })
            except Exception:
                pass
        return voices

    def get_status(self) -> dict:
        return {
            "enabled": self.enabled,
            "engine": self.engine_name,
            "voice_id": self.voice_id,
            "rate": self.rate,
        }


# Singleton
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service

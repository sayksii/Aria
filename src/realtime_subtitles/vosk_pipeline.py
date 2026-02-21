"""
Unified Streaming Pipeline for real-time transcription.

Uses the best engine for each language:
- Chinese (zh): Sherpa-ONNX (high accuracy)
- English (en): Sherpa-ONNX (high accuracy)
- Japanese (ja): Vosk (Sherpa doesn't support Japanese)
"""

import threading
import queue
import time
from typing import Optional, Callable, Union
import numpy as np

from .audio.capture import AudioCapture
from .pipeline import SubtitleEvent
from .logger import info, debug, warning, error, transcript

# Import transcribers with fallbacks
try:
    from .transcription.sherpa_transcriber import SherpaTranscriber, SHERPA_AVAILABLE
except ImportError:
    SHERPA_AVAILABLE = False
    SherpaTranscriber = None

try:
    from .transcription.vosk_transcriber import VoskTranscriber, VOSK_AVAILABLE
except ImportError:
    VOSK_AVAILABLE = False
    VoskTranscriber = None

# Translation support (optional)
try:
    from .translation.translator import create_translator, CTRANSLATE2_AVAILABLE, GOOGLETRANS_AVAILABLE
    TRANSLATION_AVAILABLE = CTRANSLATE2_AVAILABLE or GOOGLETRANS_AVAILABLE
    debug(f"Translation module loaded, CTRANSLATE2={CTRANSLATE2_AVAILABLE}, GOOGLE={GOOGLETRANS_AVAILABLE}")
except ImportError as e:
    warning(f"Translation import failed: {e}")
    TRANSLATION_AVAILABLE = False
    create_translator = None

# TranslationStateManager for incremental translation (matches LiveCaptions logic)
from .livecaptions.manager import TranslationStateManager


class StreamingPipeline:
    """
    Unified streaming transcription pipeline.
    
    Automatically selects the best engine for each language:
    - zh/en: Sherpa-ONNX (better accuracy)
    - ja: Vosk (Sherpa doesn't have Japanese model)
    """
    
    # Engine selection by language
    ENGINE_MAP = {
        "zh": "sherpa",
        "en": "sherpa",
        "ja": "vosk",
    }
    
    def __init__(
        self,
        language: str = "zh",
        on_subtitle: Optional[Callable[[SubtitleEvent], None]] = None,
        max_lines: int = 4,
        # Translation settings
        enable_translation: bool = False,
        translation_engine: str = "google",
        target_language: str = "zh",
        audio_source: str = "system",
    ):
        """
        Initialize the streaming pipeline.
        
        Args:
            language: Language code (zh, en, ja)
            on_subtitle: Callback for subtitle events
            max_lines: Maximum lines to display
            enable_translation: Whether to enable translation
            translation_engine: "google" or "nllb"
            target_language: Target language for translation
        """
        self.language = language
        self.on_subtitle = on_subtitle or self._default_callback
        self.max_lines = max_lines
        self.enable_translation = enable_translation
        self.translation_engine = translation_engine
        self.target_language = target_language
        
        # Determine which engine to use
        engine = self.ENGINE_MAP.get(language, "sherpa")
        
        # Create transcriber based on engine
        if engine == "sherpa":
            if not SHERPA_AVAILABLE:
                raise ImportError("sherpa-onnx is required. Run: pip install sherpa-onnx")
            self._transcriber = SherpaTranscriber(language=language)
            self._engine_name = "Sherpa"
        else:  # vosk
            if not VOSK_AVAILABLE:
                raise ImportError("Vosk is required. Run: pip install vosk")
            self._transcriber = VoskTranscriber(language=language)
            self._engine_name = "Vosk"
        
        # Translation (optional) - now using TranslationStateManager
        self._translator = None
        self._state_manager = None
        if enable_translation and TRANSLATION_AVAILABLE:
            try:
                self._translator = create_translator(
                    engine=translation_engine,
                    target_language=target_language,
                )
                # Initialize TranslationStateManager with translator function
                self._state_manager = TranslationStateManager(
                    translator=self._translator.translate
                )
                debug(f"StreamingPipeline: TranslationStateManager initialized")
            except Exception as e:
                warning(f"Translation init failed: {e}")
                self._translator = None
                self._state_manager = None
        
        # Audio capture
        self._audio_capture = AudioCapture(
            source=audio_source,
        )
        
        # State
        self._running = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._process_thread: Optional[threading.Thread] = None
        
        # Async Conflation State (for buffering ASR while translating)
        self._latest_raw_text: str = ""
        self._new_text_event = threading.Event()
        self._text_lock = threading.Lock()
        self._translation_thread: Optional[threading.Thread] = None
        
        trans_status = "enabled (incremental)" if self._state_manager else "disabled"
        info(f"Using {self._engine_name} for {language}, translation={trans_status}")
    
    def _default_callback(self, event: SubtitleEvent) -> None:
        """Default subtitle callback."""
        debug(f"[{event.language}] {event.text}")
    
    def _on_audio(self, audio: np.ndarray, sample_rate: int) -> None:
        """Callback from AudioCapture."""
        self._audio_queue.put(audio)
    
    def _process_loop(self) -> None:
        """
        ASR Thread: High-speed audio processing.
        Produces raw text stream, never blocks on translation.
        """
        while self._running:
            try:
                audio = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # Process with transcriber (Fast, local C++ call)
            # Returns continuous raw text stream
            raw_text = self._transcriber.process_audio(audio)
            
            # Check for changes to avoid redundant updates
            # (Sherpa/Vosk returns same text repeatedly until new audio changes it)
            if not raw_text or raw_text == self._latest_raw_text:
                continue
            
            # Update latest text safely
            with self._text_lock:
                self._latest_raw_text = raw_text
                self._new_text_event.set()  # Signal translation thread

            transcript(raw_text)
            
            # If no translation is enabled, we need to emit here immediately
            # otherwise we won't see anything. 
            if not self._state_manager:
                # Emit raw text immediately (no translation)
                event = SubtitleEvent(
                    text=raw_text,
                    language=self.language,
                    confidence=1.0,
                    timestamp=time.time(),
                    is_partial=True,
                    committed_translation="",
                    draft_translation="",
                    target_language=None,
                )
                self.on_subtitle(event)

    def _translation_loop(self) -> None:
        """
        Translation Thread: Low-speed translation processing.
        Consumes latest raw text, blocks on network calls (Google/NLLB).
        Conflates updates (skips intermediate frames if falling behind).
        """
        while self._running:
            # Wait for new text (with timeout to allow checking _running)
            if not self._new_text_event.wait(timeout=0.1):
                continue
            
            # Get latest text and clear flag
            raw_text = ""
            with self._text_lock:
                raw_text = self._latest_raw_text
                self._new_text_event.clear()
            
            if not raw_text or not self._state_manager:
                continue
                
            try:
                # BLOCKS HERE: TranslationStateManager calls network translator
                state = self._state_manager.process_text(raw_text)
                if state.committed_text:
                    transcript(state.committed_text)
                if state.draft_text:
                    transcript(state.draft_text)
                
                # Emit translated event
                event = SubtitleEvent(
                    text=raw_text,
                    language=self.language,
                    confidence=1.0,
                    timestamp=time.time(),
                    is_partial=True,
                    committed_translation=state.committed_text,
                    draft_translation=state.draft_text,
                    target_language=self.target_language,
                )
                self.on_subtitle(event)
                
            except Exception as e:
                warning(f"StreamingPipeline: Translation error: {e}")

    def start(self) -> None:
        """Start the streaming pipeline."""
        if self._running:
            return
        
        self._running = True
        
        # Reset state
        self._latest_raw_text = ""
        self._new_text_event.clear()
        
        # Reset state manager for fresh start
        if self._state_manager:
            self._state_manager.reset()
        
        # Start threads
        self._process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name="StreamingPipeline_ASR"
        )
        self._process_thread.start()
        
        if self._state_manager:
            self._translation_thread = threading.Thread(
                target=self._translation_loop,
                daemon=True,
                name="StreamingPipeline_Translation"
            )
            self._translation_thread.start()
        
        # Start audio capture
        self._audio_capture.start(callback=self._on_audio)
        
        info(f"StreamingPipeline started ({self._engine_name})")
    
    def stop(self) -> None:
        """Stop the pipeline."""
        self._running = False
        self._new_text_event.set() # Wake up translation thread
        
        self._audio_capture.stop()
        
        if self._process_thread:
            self._process_thread.join(timeout=2.0)
        
        if self._translation_thread:
            self._translation_thread.join(timeout=2.0)
        
        # Clear queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        
        info("StreamingPipeline stopped")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# Backward compatibility alias
VoskStreamingPipeline = StreamingPipeline

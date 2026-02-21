"""
System audio capture using WASAPI loopback.

This module captures audio output from the system (what you hear through speakers)
using Windows Audio Session API (WASAPI) in loopback mode.
"""

import threading
import queue
from typing import Callable, Optional
import numpy as np
from ..logger import info, debug, warning

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    pyaudio = None


class AudioCapture:
    """
    Captures system audio using WASAPI loopback mode.
    
    This allows capturing any audio playing through the system's
    default output device (speakers/headphones).
    
    Example:
        >>> capture = AudioCapture()
        >>> capture.start(callback=lambda audio, sr: print(f"Got {len(audio)} samples"))
        >>> # ... do something ...
        >>> capture.stop()
    """
    
    # Audio settings optimized for Whisper
    SAMPLE_RATE = 16000  # Whisper expects 16kHz
    CHANNELS = 1  # Mono
    CHUNK_DURATION_MS = 100  # 100ms chunks for low latency

    MIC_SOURCE_PREFIX = "mic:"
    MIC_DEFAULT_SOURCE = "mic:default"
    
    def __init__(
        self,
        source: str = "system",
    ):
        self._pyaudio: Optional[object] = None
        self._stream: Optional[object] = None
        self._is_running = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._callback: Optional[Callable[[np.ndarray, int], None]] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._source = source
        if self._source == "ts_tail":
            warning("AudioCapture: 'ts_tail' has been removed, fallback to system audio")
            self._source = "system"
        
    def _get_loopback_device(self) -> dict:
        """Find the WASAPI loopback device for the default output."""
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()
            
        # Get default WASAPI output device
        wasapi_info = self._pyaudio.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_output_idx = wasapi_info["defaultOutputDevice"]
        default_output = self._pyaudio.get_device_info_by_index(default_output_idx)
        
        # Find corresponding loopback device
        for i in range(self._pyaudio.get_device_count()):
            device = self._pyaudio.get_device_info_by_index(i)
            if (device.get("isLoopbackDevice", False) and 
                device["name"].startswith(default_output["name"].split(" (")[0])):
                return device
                
        # Fallback: return default output with loopback flag
        return default_output

    @classmethod
    def list_microphone_devices(cls) -> list[dict]:
        """List available microphone input devices (excluding loopback devices)."""
        if pyaudio is None:
            return []

        pa = None
        devices: list[dict] = []
        try:
            pa = pyaudio.PyAudio()

            default_input_idx: Optional[int] = None
            try:
                default_input = pa.get_default_input_device_info()
                default_input_idx = int(default_input["index"])
            except Exception:
                default_input_idx = None

            for i in range(pa.get_device_count()):
                d = pa.get_device_info_by_index(i)
                if int(d.get("maxInputChannels", 0)) <= 0:
                    continue
                if d.get("isLoopbackDevice", False):
                    continue
                idx = int(d["index"])
                devices.append(
                    {
                        "index": idx,
                        "name": str(d["name"]),
                        "is_default": idx == default_input_idx,
                    }
                )

            devices.sort(key=lambda x: (not x["is_default"], x["name"].lower()))
            return devices
        except Exception:
            return []
        finally:
            if pa is not None:
                pa.terminate()

    def _get_microphone_device(self) -> dict:
        """Resolve a microphone device from source key."""
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()

        try:
            default_input = self._pyaudio.get_default_input_device_info()
        except Exception as e:
            raise RuntimeError("No microphone input device available.") from e

        if self._source == self.MIC_DEFAULT_SOURCE:
            return default_input

        if self._source.startswith(self.MIC_SOURCE_PREFIX):
            idx_text = self._source.split(":", 1)[1]
            try:
                index = int(idx_text)
                device = self._pyaudio.get_device_info_by_index(index)
                if int(device.get("maxInputChannels", 0)) <= 0:
                    raise RuntimeError(f"Selected microphone device is not an input device: {index}")
                return device
            except ValueError:
                return default_input
            except Exception as e:
                raise RuntimeError(f"Failed to open selected microphone device: {idx_text}") from e

        return default_input
    
    def _calculate_chunk_size(self, device_rate: int) -> int:
        """Calculate chunk size in frames based on device sample rate."""
        return int(device_rate * self.CHUNK_DURATION_MS / 1000)
    
    def _resample(self, audio: np.ndarray, original_rate: int) -> np.ndarray:
        """Resample audio to target sample rate using linear interpolation."""
        if original_rate == self.SAMPLE_RATE:
            return audio
            
        # Simple resampling using numpy interpolation
        duration = len(audio) / original_rate
        target_length = int(duration * self.SAMPLE_RATE)
        
        if target_length == 0:
            return np.array([], dtype=np.float32)
            
        indices = np.linspace(0, len(audio) - 1, target_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback - runs in separate thread."""
        self._audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def _process_audio_loop(self, device_rate: int, channels: int):
        """Main loop for processing captured audio."""
        while self._is_running:
            try:
                raw_data = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            # Convert bytes to numpy array
            audio = np.frombuffer(raw_data, dtype=np.float32)
            
            # Convert stereo to mono if needed
            if channels > 1:
                audio = audio.reshape(-1, channels).mean(axis=1)
            
            # Resample to 16kHz
            audio = self._resample(audio, device_rate)
            
            # Call user callback
            if self._callback and len(audio) > 0:
                self._callback(audio, self.SAMPLE_RATE)
    
    def start(self, callback: Callable[[np.ndarray, int], None]) -> None:
        """
        Start capturing system audio.
        
        Args:
            callback: Function called with (audio_chunk: np.ndarray, sample_rate: int)
                     for each captured audio chunk.
        """
        if self._is_running:
            return
            
        self._callback = callback
        self._is_running = True

        # Default: WASAPI loopback (system) or microphone input
        if pyaudio is None:
            self._is_running = False
            raise ImportError(
                "pyaudiowpatch is required for audio capture. "
                "Install it with: pip install PyAudioWPatch"
            )
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()

        if self._source == "system":
            device = self._get_loopback_device()
            source_name = "system audio"
        elif self._source.startswith(self.MIC_SOURCE_PREFIX):
            device = self._get_microphone_device()
            source_name = "microphone"
        else:
            device = self._get_loopback_device()
            source_name = "system audio"

        device_rate = int(device["defaultSampleRate"])
        channels = int(device["maxInputChannels"])
        chunk_size = self._calculate_chunk_size(device_rate)

        info(f"AudioCapture: Using {source_name} device: {device['name']}")
        info(f"AudioCapture: Device rate: {device_rate}Hz, Channels: {channels}")
        debug(f"AudioCapture: Chunk size: {chunk_size} frames ({self.CHUNK_DURATION_MS}ms)")

        self._stream = self._pyaudio.open(
            format=pyaudio.paFloat32,
            channels=channels,
            rate=device_rate,
            input=True,
            input_device_index=device["index"],
            frames_per_buffer=chunk_size,
            stream_callback=self._audio_callback,
        )

        self._capture_thread = threading.Thread(
            target=self._process_audio_loop,
            args=(device_rate, channels),
            daemon=True,
        )
        self._capture_thread.start()

        self._stream.start_stream()
        info(f"AudioCapture: Started capturing {source_name}")
    
    def stop(self) -> None:
        """Stop capturing audio."""
        self._is_running = False
        
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
            
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None

        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None
            
        # Clear queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
                
        info("AudioCapture: Stopped")

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# Quick test
if __name__ == "__main__":
    import time
    
    def on_audio(audio: np.ndarray, sample_rate: int):
        # Calculate audio level (RMS)
        rms = np.sqrt(np.mean(audio ** 2))
        db = 20 * np.log10(max(rms, 1e-10))
        bars = int(max(0, (db + 60) / 2))  # -60dB to 0dB -> 0 to 30 bars
        print(f"\r[{'█' * bars}{' ' * (30 - bars)}] {db:6.1f} dB", end="", flush=True)
    
    print("Testing audio capture... Play some audio on your computer!")
    print("Press Ctrl+C to stop.\n")
    
    capture = AudioCapture()
    try:
        capture.start(callback=on_audio)
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        capture.stop()

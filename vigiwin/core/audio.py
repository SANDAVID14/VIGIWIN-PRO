"""
VIGI-WIN PRO - Generador y Reproductor de Audio Local
Genera tonos de alerta, sirenas y campanadas sin requerir archivos externos ni conexión a Internet.
Utiliza la API nativa de Windows (winsound) de forma asíncrona para no congelar la UI.
"""
import io
import wave
import math
import struct
import threading
import sys

class AudioManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
            cls._instance._init_sounds()
        return cls._instance

    def _init_sounds(self):
        self.muted = False
        self.volume = 100
        # Pre-generar buffers WAV en memoria para reproducción instantánea sin latencia
        self._chime_wav = self._generate_tone_wav([
            (880, 0.12, 0.3),  # La5
            (1174, 0.18, 0.25) # Re6
        ])
        self._alarm_siren_wav = self._generate_siren_wav(duration=1.2, base_freq=650, mod_freq=950)
        self._gentle_notice_wav = self._generate_tone_wav([
            (523, 0.1, 0.2),  # Do5
            (659, 0.15, 0.2)  # Mi5
        ])

    def _generate_tone_wav(self, notes, sample_rate=44100):
        """Genera un archivo WAV en memoria compuesto por una secuencia de notas (frecuencia, duración, amplitud)."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            
            for freq, duration, amp in notes:
                num_samples = int(sample_rate * duration)
                data = bytearray()
                for i in range(num_samples):
                    t = float(i) / sample_rate
                    # Decay envolvente exponencial suave para evitar chasquidos
                    envelope = math.exp(-3.0 * (t / duration))
                    val = math.sin(2.0 * math.pi * freq * t) * amp * envelope
                    sample = int(val * 32767.0)
                    sample = max(-32768, min(32767, sample))
                    data.extend(struct.pack('<h', sample))
                wav.writeframes(data)
        return buffer.getvalue()

    def _generate_siren_wav(self, duration=1.2, base_freq=600, mod_freq=1000, sample_rate=44100):
        """Genera una sirena de alerta prioritaria bitonal oscilante."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            
            num_samples = int(sample_rate * duration)
            data = bytearray()
            phase = 0.0
            for i in range(num_samples):
                t = float(i) / sample_rate
                # Frecuencia oscilante a 3 Hz
                current_freq = base_freq + (mod_freq - base_freq) * (0.5 * (1.0 + math.sin(2.0 * math.pi * 3.0 * t)))
                phase += 2.0 * math.pi * current_freq / sample_rate
                val = math.sin(phase) * 0.4
                sample = int(val * 32767.0)
                sample = max(-32768, min(32767, sample))
                data.extend(struct.pack('<h', sample))
            wav.writeframes(data)
        return buffer.getvalue()

    def play_sound_async(self, sound_bytes, fallback_freq=1000, fallback_dur=300):
        """Reproduce sonido en un hilo separado con fallback automático a beeps de hardware."""
        if self.muted:
            return

        def _play():
            played = False
            if sys.platform == 'win32':
                try:
                    import winsound
                    winsound.PlaySound(sound_bytes, winsound.SND_MEMORY)
                    played = True
                except Exception as e:
                    print(f"[AUDIO] PlaySound en memoria no disponible: {e}")
                if not played:
                    try:
                        import winsound
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                        winsound.Beep(fallback_freq, fallback_dur)
                    except Exception:
                        pass

        threading.Thread(target=_play, daemon=True).start()

    def play_chime(self):
        """Sonido de notificación agradable."""
        self.play_sound_async(self._chime_wav, fallback_freq=880, fallback_dur=250)

    def play_critical_alarm(self):
        """Sonido de alarma crítica prioritaria con sirena de alta frecuencia."""
        self.play_sound_async(self._alarm_siren_wav, fallback_freq=1200, fallback_dur=600)

    def play_door_closed_notice(self):
        """Sonido suave de confirmación al cerrarse la puerta."""
        self.play_sound_async(self._gentle_notice_wav, fallback_freq=659, fallback_dur=200)

    def beep(self, frequency=1000, duration_ms=200):
        """Emite un beep simple de hardware de Windows."""
        if self.muted:
            return
        def _beep():
            try:
                if sys.platform == 'win32':
                    import winsound
                    winsound.Beep(frequency, duration_ms)
            except Exception:
                pass
        threading.Thread(target=_beep, daemon=True).start()

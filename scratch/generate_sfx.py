import wave
import math
import struct
import random

def generate_tone(filename, duration, freq_func, volume=0.3, sample_rate=44100):
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(int(sample_rate * duration)):
            t = float(i) / sample_rate
            freq = freq_func(t)
            
            # Simple envelope to prevent clicking
            env = 1.0
            if t < 0.05: env = t / 0.05
            elif t > duration - 0.05: env = (duration - t) / 0.05
            
            value = int(volume * env * math.sin(2.0 * math.pi * freq * t) * 32767.0)
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

print("Generating SFX...")
# 1. Hologram Scan (Rapid frequency sweep up)
generate_tone("scratch/sfx_01_hologram_scan.wav", 1.5, lambda t: 100 + (t * 1200))

# 2. Data Processing Beeps (Random high-pitch blips)
# 15 blips per second. We modulate frequency based on time chunks.
def data_freq(t):
    chunk = int(t * 15)
    if chunk % 2 == 0:
        return [800, 1200, 1600, 2400][(chunk//2) % 4]
    return 0
generate_tone("scratch/sfx_02_data_processing.wav", 2.0, data_freq)

# 3. Warning Alert (Medical dual-tone pulse)
# Pulses 2 times a second
def alert_freq(t):
    chunk = int(t * 4)
    if chunk % 2 == 0:
        return 600
    return 0
generate_tone("scratch/sfx_03_warning_alert.wav", 1.5, alert_freq)

print("Done! Generated 3 WAV files.")

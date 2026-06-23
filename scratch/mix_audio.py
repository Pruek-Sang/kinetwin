import os
import subprocess

ffmpeg_exe = r"C:\Users\Welcome\AppData\Local\CapCut\Apps\8.6.0.3667\ffmpeg.exe"
base_dir = r"c:\Users\Welcome\Desktop\tool\KineTwin (Kinematic Digital Twin)\scratch"

speech = os.path.join(base_dir, "pitch_en_2m30s.mp3")
sfx1 = os.path.join(base_dir, "sfx_01_hologram_scan.wav")
sfx2 = os.path.join(base_dir, "sfx_02_data_processing.wav")
sfx3 = os.path.join(base_dir, "sfx_03_warning_alert.wav")
bgm = os.path.join(base_dir, "sfx_04_ambient_bgm.mp3")
out_path = os.path.join(base_dir, "pitch_en_2m30s_mixed.wav")

# Speed up factor
speed = 1.08

# Timings in milliseconds (original time / speed)
delay1 = int((38 / speed) * 1000)
delay2 = int((62 / speed) * 1000)
delay3 = int((82 / speed) * 1000)

filter_complex = (
    f"[0:a]atempo={speed},volume=1.5[speech]; "
    f"[1:a]adelay={delay1}|{delay1}[s1]; "
    f"[2:a]adelay={delay2}|{delay2}[s2]; "
    f"[3:a]adelay={delay3}|{delay3}[s3]; "
    f"[4:a]volume=0.15[bg]; "
    f"[speech][s1][s2][s3][bg]amix=inputs=5:duration=first[out]"
)

cmd = [
    ffmpeg_exe,
    "-y",  # overwrite
    "-i", speech,
    "-i", sfx1,
    "-i", sfx2,
    "-i", sfx3,
    "-i", bgm,
    "-filter_complex", filter_complex,
    "-map", "[out]",
    "-c:a", "pcm_s16le",
    out_path
]

print("Running FFmpeg to mix audio...")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    print(f"Success! Mixed audio saved to {out_path}")
else:
    print("FFmpeg failed!")
    print(result.stderr)

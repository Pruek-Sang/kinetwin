import os
from gtts import gTTS

def generate_speech():
    input_path = "scratch/pitch_en_2m30s.txt"
    output_path = "scratch/pitch_en_2m30s.mp3"
    
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return
        
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip sound cues, headers, and comments
        if stripped.startswith("[") or stripped.startswith("#"):
            continue
        if stripped:
            clean_lines.append(stripped)
            
    clean_text = "\n".join(clean_lines)
    print("Cleaned text to synthesize:")
    print(clean_text)
    
    print("\nSynthesizing speech...")
    tts = gTTS(text=clean_text, lang='en', slow=False)
    tts.save(output_path)
    print(f"Success! Speech saved to {output_path}")

if __name__ == "__main__":
    generate_speech()

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import subprocess
import ssl
import ffmpeg
import threading
import time
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from googletrans import Translator
import whisper  # Import Whisper here

progress = 0

ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)
translator = Translator()

# Load Whisper model once
model = whisper.load_model("base")  # Adjust based on your needs

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    file = request.files.get('file')

    if not file:
        return jsonify({"error": "No file received"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    subtitle_path = os.path.join(UPLOAD_FOLDER, os.path.splitext(file.filename)[0] + ".vtt")

    file.save(file_path)

    # Generate subtitles only if they don't already exist
    if not os.path.exists(subtitle_path):
        subtitle_path = extract_subtitles(file_path)
        if not subtitle_path:
            return jsonify({"error": "Failed to generate subtitles"}), 500

    return jsonify({
        "message": "File uploaded successfully",
        "video_path": file.filename,  # Return exact filename for frontend
        "subtitle_path": os.path.basename(subtitle_path)
    })



@app.route('/get_video', methods=['GET'])
def get_video():
    video_path = request.args.get('video_path')
    full_video_path = os.path.join(UPLOAD_FOLDER, video_path)

    if not os.path.exists(full_video_path):
        return jsonify({"error": "Video not found"}), 404
    return send_file(full_video_path)

@app.route('/translate', methods=['POST'])
def translate_subtitles():
    global progress
    progress = 0

    video_file_path = request.json.get('video_file_path')
    target_language = request.json.get('target_language')

    if not video_file_path or not target_language:
        return jsonify({"error": "No video file path or target language provided."}), 400

    full_video_path = os.path.join(UPLOAD_FOLDER, video_file_path)
    subtitle_path = extract_subtitles(full_video_path)

    if not subtitle_path:
        return jsonify({"error": "No subtitles found in video."}), 400

    def translate_and_save_subtitles():
        global progress
        with open(subtitle_path, "r", encoding="utf-8") as f:
            subtitles = f.readlines()

        translated_subtitles = []
        for index, line in enumerate(subtitles):
            if '-->' in line:
                translated_subtitles.append(line)  
            else:
                if line.strip():  
                    translated_line = translator.translate(line, src="en", dest=target_language).text
                    translated_subtitles.append(translated_line if translated_line else line)
                else:
                    translated_subtitles.append(line)

            progress = int((index / len(subtitles)) * 100)
            time.sleep(0.1)  

        translated_subtitle_path = os.path.join(UPLOAD_FOLDER, "translated_subtitles.vtt")
        with open(translated_subtitle_path, "w", encoding="utf-8") as f:
            index = 1
            for line in translated_subtitles:
                if '-->' in line:
                    f.write(f"{index}\n")
                    index += 1
                    f.write(line.strip() + "\n")
                else:
                    f.write(line.strip() + "\n")

        video_with_subtitles_path = os.path.join(UPLOAD_FOLDER, f"Test_with_{target_language}_subtitles.mp4")
        video_with_subtitles = add_subtitles_to_video(full_video_path, translated_subtitle_path, video_with_subtitles_path)

        if video_with_subtitles:
            progress = 100
        else:
            progress = 0

    threading.Thread(target=translate_and_save_subtitles, daemon=True).start()

    return jsonify({"message": "Translation started. Check progress using the /progress endpoint."})

 

@app.route('/download_video_with_subtitles', methods=['GET'])
def download_video_with_subtitles():
    video_path = os.path.join(UPLOAD_FOLDER, "Test_with_fa_subtitles.mp4")

    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=True)
    else:
        return jsonify({"error": "Translated video file not found."}), 404

@app.route('/download_translated_subtitles', methods=['GET'])
def download_translated_subtitles():
    path_to_subtitles_file = os.path.join(UPLOAD_FOLDER, "translated_subtitles.vtt")

    if os.path.exists(path_to_subtitles_file):
        return send_file(path_to_subtitles_file, as_attachment=True)
    else:
        return jsonify({"error": "Translated subtitles file not found."}), 404

def extract_subtitles(video_path):
    try:
        result = model.transcribe(video_path)
        subtitle_path = video_path.rsplit('.', 1)[0] + ".vtt"
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for segment in result["segments"]:
                start = segment["start"]
                end = segment["end"]
                text = segment["text"]
                f.write(f"{start:.2f} --> {end:.2f}\n{text}\n\n")
        return subtitle_path
    except Exception as e:
        print(f"Error extracting subtitles: {e}")
        return None
    
@app.route('/get_subtitles')
def get_subtitles():
    video_path = request.args.get('video_path')
    if not video_path:
        return jsonify({"error": "Video path not provided"}), 400

    subtitle_path = os.path.join(UPLOAD_FOLDER, os.path.splitext(video_path)[0] + ".vtt")

    if os.path.exists(subtitle_path):
        return send_file(subtitle_path, as_attachment=True)
    else:
        return jsonify({"error": "Subtitles file not found."}), 404

def add_subtitles_to_video(video_path, subtitle_path, output_path):
    try:
        command = [
            'ffmpeg', '-i', video_path, '-i', subtitle_path,
            '-c:v', 'copy', '-c:a', 'aac', '-c:s', 'mov_text',
            '-strict', 'experimental', '-y', output_path
        ]
        subprocess.run(command, check=True)
        return output_path
    except Exception as e:
        print(f"Error adding subtitles to video: {e}")
        return None

@app.route('/progress', methods=['GET'])
def get_progress():
    global progress
    return jsonify({"progress": progress})

if __name__ == '__main__':
    app.run(debug=True)

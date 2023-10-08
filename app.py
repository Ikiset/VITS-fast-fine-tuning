import os
import time # Temporaire
import shutil
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename

from scripts.short_audio_transcribe import short_audio_transcribe
from scripts.resample import run_resample
from preprocess import preprocess

app = Flask(__name__)
app.secret_key = 'azerty'

UPLOAD_FOLDER = './custom_character_voice/'

@app.route('/')
def home():
    return render_template('index.html')
	
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "File not found"})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "File not found"})
    
    try:
        file.save(UPLOAD_FOLDER + secure_filename(file.filename))
        return jsonify({"success": "File successfully loaded"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/get_uploaded_files')
def get_uploaded_files():
    uploaded_files = os.listdir(UPLOAD_FOLDER)
    return jsonify(files=uploaded_files)

def processing_short_audio():
    if 'progress' not in session:
        generator_audio_transcribe = short_audio_transcribe()
        session['progress'] = next(generator_audio_transcribe)
        number_file = session['progress'][1]
    while session['progress'] != "finished":
        if 'stop_processing' in session and session['stop_processing']:
            yield "stopped"
            break
        progress, total, error_audio, error_lang = session['progress']
        yield f"{progress}/{total}\n\t{error_audio}\n\t{error_lang}"
        session['progress'] = next(generator_audio_transcribe)
    add_auxiliary_data = number_file < 600
    if add_auxiliary_data:
        run_resample()
    preprocess(add_auxiliary_data)

@app.route('/preprocess')
def preprocess_page():
    session.pop('progress', None)
    if session['stop_processing'] == True:
        session['stop_processing'] = False
    return jsonify({'message': 'Preprocess starting'})

@app.route('/get_progress')
def get_progress():
    progress_generator = processing_short_audio()
    try:
        progress = next(progress_generator)
        return jsonify({'progress': progress})
    except StopIteration:
        return jsonify({'progress': "ended"})

@app.route('/stop_processing')
def stop_processing():
    session['stop_processing'] = True
    return jsonify({'message': 'Le traitement sera arrêté après la prochaine étape'})

@app.route('/remove_all')
def remove_all_file():
    try:
        shutil.rmtree(UPLOAD_FOLDER)
        os.makedirs(UPLOAD_FOLDER)
        return jsonify({'message': 'Tous les fichiers ont été supprimés avec succès'})
    except Exception as e:
        return jsonify({'error': 'Erreur lors de la suppression des fichiers', 'details': str(e)})

@app.route('/train')
def start_training():
    

if __name__ == '__main__':
    app.run(app, debug=True)
# To run
# flask run --host=0.0.0.0 --port=8080
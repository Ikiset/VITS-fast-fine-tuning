import os
import time  # Temporaire
import shutil
from flask import Flask, render_template, request, jsonify, session, send_from_directory, send_file
from werkzeug.utils import secure_filename

import torch
from torch import no_grad, LongTensor
from models import SynthesizerTrn
from text import symbols, text_to_sequence
import utils
import commons
import numpy as np
from scipy.io import wavfile

app = Flask(__name__)
app.secret_key = 'azerty'

UPLOAD_FOLDER = './custom_character_voice/'
UPLOAD_MODEL = './pretrained_models/'

global_stop = False
i = 0

device = "cuda:0" if torch.cuda.is_available() else "cpu"
hps = utils.get_hparams_from_file("configs/finetune_speaker.json")

model = SynthesizerTrn(
    len(symbols),
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    n_speakers=hps.data.n_speakers,
    **hps.model).to(device)
_ = model.eval()
model_dir = 'OUTPUT_MODELS/G_latest.pth'
if not os.path.exists(model_dir):
    model_dir = ''
    _ = utils.load_checkpoint('pretrained_models/G_0.pth', model, None)
else:
    _ = utils.load_checkpoint(model_dir, model, None)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"message": "Error : File not found"})

    file = request.files['file']

    if file.filename == '':
        return jsonify({"message": "Error : File not found"})

    try:
        file.save(UPLOAD_FOLDER + secure_filename(file.filename))
        return jsonify({"message": "File successfully loaded"})
    except Exception as e:
        return jsonify({"message": str(e)})


@app.route('/get_uploaded_files')
def get_uploaded_files():
    uploaded_files = os.listdir(UPLOAD_FOLDER)
    return jsonify(files=uploaded_files)


def processing_short_audio():
    from scripts.short_audio_transcribe import short_audio_transcribe
    from scripts.resample import run_resample
    from preprocess import preprocess

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


@app.route('/train/start')
def start_training():
    global global_stop
    global_stop = False
    epoch_progress_generator = get_epoch()
    tmp_epoch = None
    print((124, hps.train.epochs))
    try:
        epoch = next(epoch_progress_generator)
        tmp_epoch = epoch
        return jsonify({'epoch': str(epoch), 'max_epochs': str(hps.train.epochs), 'status': 'training'})
    except StopIteration:
        return jsonify({'epoch': str(tmp_epoch), 'max_epochs': str(hps.train.epochs), 'status': 'ended'})


def get_epoch():
    global global_stop
    global i
    while not global_stop:
        yield i


@app.route('/train/run')
def train():
    global i
    i = 0
    while(True):
        i += 1
        time.sleep(3)
        global global_stop
        if global_stop:
            exit()


@app.route('/train/stop')
def train_stop():
    global global_stop
    global i
    global_stop = True
    return jsonify({"epoch": i, "status": "stopped"})


@app.route('/train/continu')
def train_continu():
    pass


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pth'}


@app.route('/generate', methods=['GET'])
def generate_page():
    speakers = list(hps.speakers.keys())
    return render_template('generate.html', speakers=speakers)


@app.route('/upload_model', methods=['POST'])
def upload_model():
    if 'model_file' not in request.files:
        return jsonify({"message": 'Error : model is not selected'})

    file = request.files['model_file']

    if file.filename == '':
        return jsonify({"message": 'Error : model is not selected'})
    elif file.filename == 'G_0.pth' or file.filename == 'G_latest.pth':
        return jsonify({"message": 'filename can not name as G_0.pth or G_latest.pth'})
    file.save(os.path.join(UPLOAD_MODEL, file.filename))
    return jsonify({"message": 'model is successfully uploaded'})


@app.route('/delete_model', methods=['POST'])
def delete_model():
    data = request.get_json()
    model_name = data.get('model_name')
    if model_name == "G_0.pth":
        return jsonify({'error': f'This model {model_name} can not be delete'})
    if model_name == '':
        return jsonify({'error': 'Model not found'})
    upload_model_path = os.path.join(UPLOAD_MODEL, model_name)
    if os.path.exists(upload_model_path):
        os.remove(upload_model_path)
        return jsonify({'message': f'{model_name} model is successfully delete'})

    return jsonify({'error': f'{model_name} model not found'})


@app.route('/get_models')
def get_models():
    models = [f for f in os.listdir(UPLOAD_MODEL) if os.path.isfile(
        os.path.join(UPLOAD_MODEL, f))]
    if os.path.exists("OUTPUT_MODELS/G_latest.pth"):
        models.insert(0, "your trained model")
    return jsonify({'models': models})


@app.route('/generate_text', methods=['POST'])
def generate_text():
    data = request.get_json()
    text = data.get('text')
    speakerID = int(data.get('speaker'))
    speed = 1
    text_data = get_text(text)
    with no_grad():
        x_data = text_data.unsqueeze(0).to(device)
        x_data_lenghts = LongTensor([text_data.size(0)]).to(device)
        sid = LongTensor([speakerID]).to(device)
        audio = model.infer(x_data, x_data_lenghts, sid=sid, noise_scale=.667, noise_scale_w=0.8,
                            length_scale=1.0 / speed)[0][0, 0].data.cpu().float().numpy
    wavfile.write("output.wav", hps.data.sampling_rate, audio())
    # text, speakerID
    return jsonify({'message': "wav is succefully generate"})


def get_text(text):
    text_norm = text_to_sequence(text, symbols, hps.data.text_cleaners)
    if hps.data.add_blank:
        text_norm = commons.intersperse(text_norm, 0)
    text_norm = LongTensor(text_norm)
    return text_norm


@app.route('/generate/wav')
def load_generate_wav():
    return send_from_directory(os.getcwd(), 'output.wav')


@app.route('/generate/download')
def download_audio():
    return send_file("output.wav", mimetype="audio/wav", as_attachment=True)


if __name__ == '__main__':
    app.run(app, debug=True)
# To run
# flask run --host=0.0.0.0 --port=8080

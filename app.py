import os
import time  # Temporaire
import shutil
from flask import Flask, render_template, request, jsonify, session, send_from_directory, send_file
from werkzeug.utils import secure_filename
from train_utils import global_step, global_stop
import torch
from torch import no_grad, LongTensor
from models import SynthesizerTrn
from text import symbols, text_to_sequence
import utils
import commons
import numpy as np
from scipy.io import wavfile
import whisper

app = Flask(__name__)
app.secret_key = 'azerty'

UPLOAD_FOLDER = './custom_character_voice/'
UPLOAD_MODEL = './pretrained_models/'

device = "cuda:0" if torch.cuda.is_available() else "cpu"
hps = utils.get_hparams_from_file("configs/finetune_speaker.json")

model = SynthesizerTrn(
    len(symbols),
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    n_speakers=hps.data.n_speakers,
    **hps.model).to(device)
_ = model.eval()
model_dir = 'OUTPUT_MODEL/G_latest.pth'
if not os.path.exists(model_dir):
    model_dir = ''
    if os.path.exists('pretrained_models/G_0.pth'):
        _ = utils.load_checkpoint('pretrained_models/G_0.pth', model, None)
else:
    _ = utils.load_checkpoint(model_dir, model, None)

processed_files = 0
total_files = 0
stop_processing = False


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
    import torch
    import torchaudio
    from scripts.resample import run_resample
    from preprocess import preprocess
    assert (torch.cuda.is_available()
            ), "Please enable GPU in order to run Whisper!"
    model = whisper.load_model("small")

    def transcribe_one(audio_path):
        # load audio and pad/trim it to fit 30 seconds
        global stop_processing
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)

        # make log-Mel spectrogram and move to the same device as the model
        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        # detect the spoken language
        _, probs = model.detect_language(mel)
        print(
            f"{stop_processing} Detected language: {max(probs, key=probs.get)}")
        lang = max(probs, key=probs.get)
        # decode the audio
        options = whisper.DecodingOptions(beam_size=5)
        result = whisper.decode(model, mel, options)

        # print the recognized text
        print(result.text)
        return lang, result.text

    def short_audio_load(i, parent_dir, speaker, wavfile, target_sr):
        wav, sr = torchaudio.load(parent_dir + speaker + "/" + wavfile, frame_offset=0, num_frames=-1, normalize=True,
                                  channels_first=True)
        wav = wav.mean(dim=0).unsqueeze(0)
        if sr != target_sr:
            wav = torchaudio.transforms.Resample(
                orig_freq=sr, new_freq=target_sr)(wav)
        if wav.shape[1] / sr > 20:
            print(f"{wavfile} too long, ignoring")
            return None
        save_path = parent_dir + speaker + "/" + f"processed_{i}.wav"
        torchaudio.save(save_path, wav, target_sr, channels_first=True)
        return save_path

    def short_audio_transcribe():
        import os
        import json

        global processed_files
        global total_files
        global stop_processing
        parent_dir = "./custom_character_voice/"
        speaker_names = list(os.walk(parent_dir))[0][1]
        speaker_annos = []
        total_files = sum(
            [
                len([i
                     for i in os.listdir("./custom_character_voice/" + speaker)
                     if not i.startswith("processed_")
                     ])
                for speaker in speaker_names
            ])
        with open("./configs/finetune_speaker.json", 'r', encoding='utf-8') as f:
            hps = json.load(f)
        target_sr = hps['data']['sampling_rate']
        processed_files = 0
        for speaker in speaker_names:
            for i, wavfile in enumerate(list(os.walk(parent_dir + speaker))[0][2]):
                # try to load file as audio
                if stop_processing:
                    return "stopped"
                if wavfile.startswith("processed_"):
                    continue
                try:
                    save_path = short_audio_load(
                        i, parent_dir, speaker, wavfile, target_sr)
                    if save_path == None:
                        continue
                    # transcribe text
                    lang, text = transcribe_one(save_path)
                    if lang != 'fr':
                        print(f"{wavfile} : is not french")
                        continue
                    text = text + "\n"
                    speaker_annos.append(
                        save_path + "|" + speaker + "|" + text)
                    processed_files += 1
                except:
                    print(f"Error for the file : {wavfile}")
                    continue
        with open("short_character_anno.txt", 'w', encoding='utf-8') as f:
            for line in speaker_annos:
                f.write(line)
        return "ended"

    res = short_audio_transcribe()
    if res == "stopped":
        return res
    global total_files
    add_auxiliary_data = total_files < 600
    if add_auxiliary_data:
        run_resample()
    preprocess(add_auxiliary_data)
    return res


@app.route('/preprocess')
def preprocess_page():
    import zipfile
    for filename in os.listdir(UPLOAD_FOLDER):
        if filename.endswith('.zip'):
            zip_file = os.path.join(UPLOAD_FOLDER, filename)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(UPLOAD_FOLDER)
            os.remove(zip_file)
            macosx_file = os.path.join(UPLOAD_FOLDER, '__MACOSX')
            if os.path.exists(macosx_file):
                shutil.rmtree(macosx_file)
    global stop_processing
    stop_processing = False
    result = processing_short_audio()
    return jsonify({'message': result})


@app.route('/get_progress')
def get_progress():
    try:
        global processed_files
        global total_files
        return jsonify({'progress': f"{processed_files}/{total_files}"})
    except StopIteration:
        return jsonify({'progress': "ended"})


@app.route('/stop_processing')
def stop_processing():
    global stop_processing
    stop_processing = True
    return jsonify({'message': 'Le traitement sera arrêté après la prochaine étape'})


@app.route('/remove_all')
def remove_all_file():
    try:
        shutil.rmtree(UPLOAD_FOLDER)
        os.makedirs(UPLOAD_FOLDER)
        return jsonify({'message': 'Tous les fichiers ont été supprimés avec succès'})
    except Exception as e:
        return jsonify({'error': 'Erreur lors de la suppression des fichiers', 'details': str(e)})


@app.route('/train/progress')
def start_training():
    from train_utils import global_step, global_stop
    if not global_stop:
        status = 'training'
    else:
        status = 'ended'
    return jsonify({'epoch': str(global_step), 'max_epochs': str(hps.train.epochs), 'status': status})


@app.route('/train/run')
def train():
    import train_utils
    train_utils.global_stop = False
    from train_utils import train
    train()
    return jsonify({"message": 'train is over'})


@app.route('/train/stop')
def train_stop():
    import train_utils
    from train_utils import global_step, dist
    train_utils.global_stop = True
    if dist.is_initialized():
        train_utils.dist.destroy_process_group()
    return jsonify({"epoch": global_step, "status": "stopped"})


@app.route('/train/continu')
def train_continu():
    import train_utils
    train_utils.global_stop = False
    from train_utils import train
    train(cont=True)
    return jsonify({"message": 'train is over'})


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


@app.route('/generate/model', methods=['POST'])
def change_model():
    data = request.get_json()
    model_name = data.get('model_name')
    print(model_name)
    if model_name == "your trained model":
        _ = utils.load_checkpoint("./OUTPUT_MODEL/G_latest.pth", model, None)
    else:
        _ = utils.load_checkpoint(UPLOAD_MODEL + model_name, model, None)
    return jsonify({'message': f'Model is change to {model_name}'})


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
    models.remove('D_0.pth')
    if os.path.exists("OUTPUT_MODEL/G_latest.pth"):
        models.insert(0, "your trained model")
    return jsonify({'models': models})


@app.route('/generate_text', methods=['POST'])
def generate_text():
    data = request.get_json()
    text = data.get('text')
    speaker_id = int(data.get('speaker'))
    speed = 1
    text_data = get_text(text)
    with no_grad():
        x_data = text_data.unsqueeze(0).to(device)
        x_data_lenghts = LongTensor([text_data.size(0)]).to(device)
        sid = LongTensor([speaker_id]).to(device)
        audio = model.infer(x_data, x_data_lenghts, sid=sid, noise_scale=.667, noise_scale_w=0.8,
                            length_scale=1.0 / speed)[0][0, 0].data.cpu().float().numpy
    wavfile.write("output.wav", hps.data.sampling_rate, audio())
    # text, speaker_id
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

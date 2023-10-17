import os
import time  # Temporaire
import shutil
from flask import Flask, render_template, request, jsonify, session, send_from_directory, send_file
from werkzeug.utils import secure_filename
from train_utils import global_step, global_stop
import torch
import torch.distributed as dist
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

# global_stop = False
# i = 0

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
    if os.path.exists('pretrained_models/G_0.pth'):
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
    import torch
    from scripts.resample import run_resample
    from preprocess import preprocess

    assert (torch.cuda.is_available()
            ), "Please enable GPU in order to run Whisper!"
    model = whisper.load_model("small")

    def transcribe_one(audio_path):
        # load audio and pad/trim it to fit 30 seconds
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)

        # make log-Mel spectrogram and move to the same device as the model
        mel = whisper.log_mel_spectrogram(audio).to(model.device)

        # detect the spoken language
        _, probs = model.detect_language(mel)
        print(f"Detected language: {max(probs, key=probs.get)}")
        lang = max(probs, key=probs.get)
        # decode the audio
        options = whisper.DecodingOptions(beam_size=5)
        result = whisper.decode(model, mel, options)

        # print the recognized text
        print(result.text)
        return lang, result.text

    def short_audio_load(i, parent_dir, speaker, wavfile, target_sr, to_long_file, to_long_call):
        import torchaudio

        wav, sr = torchaudio.load(parent_dir + speaker + "/" + wavfile, frame_offset=0, num_frames=-1, normalize=True,
                                  channels_first=True)
        wav = wav.mean(dim=0).unsqueeze(0)
        if sr != target_sr:
            wav = torchaudio.transforms.Resample(
                orig_freq=sr, new_freq=target_sr)(wav)
        if wav.shape[1] / sr > 20:
            to_long_file.append(wavfile)
            to_long_call = f"{', '.join(to_long_file)} too long, ignoring\n"
            return None, to_long_call
        save_path = parent_dir + speaker + "/" + f"processed_{i}.wav"
        torchaudio.save(save_path, wav, target_sr, channels_first=True)
        return save_path, to_long_call

    def short_audio_transcribe():
        import os
        import json

        parent_dir = "./custom_character_voice/"
        speaker_names = list(os.walk(parent_dir))[0][1]
        speaker_annos = []
        total_files = sum([len(files) for r, d, files in os.walk(parent_dir)])
        with open("./configs/finetune_speaker.json", 'r', encoding='utf-8') as f:
            hps = json.load(f)
        target_sr = hps['data']['sampling_rate']
        processed_files = 0
        to_long_file = []
        to_long_call = ""
        lang_error_file = []
        lang_error_call = ""

        for speaker in speaker_names:
            for i, wavfile in enumerate(list(os.walk(parent_dir + speaker))[0][2]):
                # try to load file as audio
                if wavfile.startswith("processed_"):
                    continue
                try:
                    save_path, to_long_call = short_audio_load(i, parent_dir, speaker, wavfile, target_sr,
                                                               to_long_file, to_long_call)
                    if save_path == None:
                        continue
                    # transcribe text
                    lang, text = transcribe_one(save_path)
                    if lang != 'fr':
                        lang_error_file.append(wavfile+f"({lang})")
                        lang_error_call = f"{', '.join(lang_error_file)} : is not french"
                        continue
                    text = text + "\n"
                    speaker_annos.append(
                        save_path + "|" + speaker + "|" + text)

                    processed_files += 1
                    yield(processed_files, total_files, to_long_call, lang_error_call)
                except:
                    continue
        with open("short_character_anno.txt", 'w', encoding='utf-8') as f:
            for line in speaker_annos:
                f.write(line)
        yield "finished"

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
    session.pop('progress', None)
    session.pop('stop_processing', None)
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
    try:
        epoch = next(epoch_progress_generator)
        tmp_epoch = epoch
        return jsonify({'epoch': str(epoch), 'max_epochs': str(hps.train.epochs), 'status': 'training'})
    except StopIteration:
        return jsonify({'epoch': str(tmp_epoch), 'max_epochs': str(hps.train.epochs), 'status': 'ended'})


def get_epoch():
    from train_utils import global_step, global_stop
    while not global_stop:
        yield global_step


@app.route('/train/run')
def train():
    # global i
    # i = 0
    # while(True):
    #     i += 1
    #     time.sleep(3)
    #     global global_stop
    #     if global_stop:
    #         exit()
    import train_utils
    train_utils.train()


@app.route('/train/stop')
def train_stop():
    from train_utils import global_step, global_stop
    global_stop = True
    if dist.is_initialized():
        dist.destroy_process_group()
    return jsonify({"epoch": global_step, "status": "stopped"})


@app.route('/train/continu')
def train_continu():
    pass


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

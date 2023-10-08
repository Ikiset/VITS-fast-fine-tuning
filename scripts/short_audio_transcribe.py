import whisper
import os
import json
import torchaudio
import argparse
import torch

lang2token = {
            'fr': ""
        }
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
    wav, sr = torchaudio.load(parent_dir + speaker + "/" + wavfile, frame_offset=0, num_frames=-1, normalize=True,
                              channels_first=True)
    wav = wav.mean(dim=0).unsqueeze(0)
    if sr != target_sr:
        wav = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)(wav)
    if wav.shape[1] / sr > 20:
        to_long_file.append(wavfile)
        to_long_call = f"{', '.join(to_long_file)} too long, ignoring\n"
        return None, to_long_call
    save_path = parent_dir + speaker + "/" + f"processed_{i}.wav"
    torchaudio.save(save_path, wav, target_sr, channels_first=True)
    return save_path, to_long_call

def short_audio_transcribe(whisper_size="small"):
    lang2token = {'fr': "[FR]"}
    assert (torch.cuda.is_available()), "Please enable GPU in order to run Whisper!"
    model = whisper.load_model(whisper_size)
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
                if lang not in list(lang2token.keys()):
                    lang_error_file.append(wavfile+f"({lang})")
                    lang_error_call = f"{', '.join(lang_error_file)} : not suported (filename lang)"
                    continue
                text = lang2token[lang] + text + lang2token[lang] + "\n"
                speaker_annos.append(save_path + "|" + speaker + "|" + text)
                
                processed_files += 1
                yield(processed_files, total_files, to_long_call, lang_error_call)
            except:
                continue
    with open("short_character_anno.txt", 'w', encoding='utf-8') as f:
        for line in speaker_annos:
            f.write(line)
    yield "finished"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--languages", default="FR")
    parser.add_argument("--whisper_size", default="small")
    args = parser.parse_args()
    if args.languages == "FR":
        lang2token = {
            'fr': "[FR]"
        }
    assert (torch.cuda.is_available()), "Please enable GPU in order to run Whisper!"
    model = whisper.load_model(args.whisper_size)
    parent_dir = "./custom_character_voice/"
    speaker_names = list(os.walk(parent_dir))[0][1]
    speaker_annos = []
    total_files = sum([len(files) for r, d, files in os.walk(parent_dir)])
    # resample audios
    # 2023/4/21: Get the target sampling rate
    with open("./configs/finetune_speaker.json", 'r', encoding='utf-8') as f:
        hps = json.load(f)
    target_sr = hps['data']['sampling_rate']
    processed_files = 0
    for speaker in speaker_names:
        for i, wavfile in enumerate(list(os.walk(parent_dir + speaker))[0][2]):
            # try to load file as audio
            if wavfile.startswith("processed_"):
                continue
            try:
                wav, sr = torchaudio.load(parent_dir + speaker + "/" + wavfile, frame_offset=0, num_frames=-1, normalize=True,
                                          channels_first=True)
                wav = wav.mean(dim=0).unsqueeze(0)
                if sr != target_sr:
                    wav = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)(wav)
                if wav.shape[1] / sr > 20:
                    print(f"{wavfile} too long, ignoring\n")
                save_path = parent_dir + speaker + "/" + f"processed_{i}.wav"
                torchaudio.save(save_path, wav, target_sr, channels_first=True)
                # transcribe text
                lang, text = transcribe_one(save_path)
                if lang not in list(lang2token.keys()):
                    print(f"{lang} not supported, ignoring\n")
                    continue
                text = lang2token[lang] + text + lang2token[lang] + "\n"
                speaker_annos.append(save_path + "|" + speaker + "|" + text)
                
                processed_files += 1
                print(f"Processed: {processed_files}/{total_files}")
            except:
                continue

 
    if len(speaker_annos) == 0:
        print("Warning: no short audios found, this IS expected if you have only uploaded long audios, videos or video links.")
        print("this IS NOT expected if you have uploaded a zip file of short audios. Please check your file structure or make sure your audio language is supported.")
    with open("short_character_anno.txt", 'w', encoding='utf-8') as f:
        for line in speaker_annos:
            f.write(line)
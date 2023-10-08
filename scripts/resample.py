import os
import json
import argparse
import torchaudio


def main():
    with open("./configs/finetune_speaker.json", 'r', encoding='utf-8') as f:
        hps = json.load(f)
    target_sr = hps['data']['sampling_rate']
    filelist = list(os.walk("./SIWIS"))[0][2]
    if target_sr != 22050:
        for wavfile in filelist:
            wav, sr = torchaudio.load("./SWISI" + "/" + wavfile, frame_offset=0, num_frames=-1,
                                      normalize=True, channels_first=True)
            wav = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)(wav)
            torchaudio.save("./SWISI" + "/" + wavfile, wav, target_sr, channels_first=True)

def run_resample():
    main()

if __name__ == "__main__":
    main()
    
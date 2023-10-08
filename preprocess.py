import os
import argparse
import json
import sys
sys.setrecursionlimit(500000)  # Fix the error message of RecursionError: maximum recursion depth exceeded while calling a Python object.  You can change the number as you want.

def preprocess(add_auxiliary_data:bool):
    langs = ["FR"]
    if os.path.exists("short_character_anno.txt"):
        with open("short_character_anno.txt", 'r', encoding='utf-8') as f:
            short_character_anno = f.readlines()
    new_annos = [line for line in short_character_anno]
    speakers = []
    for line in new_annos :
        path, speaker, text = line.split("|")
        if speaker not in speakers:
            speakers.append(speaker)
    assert (len(speakers) != 0), "No audio file found. Please check your uploaded file structure."
    # STEP 1 : modify config file
    with open("./configs/finetune_speaker.json", 'r', encoding='utf-8') as f:
        hps = json.load(f)
    # assign ids to new speakers
    speaker2id = {}
    speaker2id = {speaker: i for i, speaker in enumerate(speakers)}
    # modify n_speakers
    hps['data']["n_speakers"] = len(speakers)
    # overwrite speaker names
    hps['speakers'] = speaker2id
    hps['train']['log_interval'] = 10
    hps['train']['eval_interval'] = 100
    hps['train']['batch_size'] = 16
    hps['data']['training_files'] = "final_annotation_train.txt"
    hps['data']['validation_files'] = "final_annotation_val.txt"
    # save modified config
    with open("./configs/finetune_speaker.json", 'w', encoding='utf-8') as f:
        json.dump(hps, f, indent=2)

    # STEP 2: clean annotations, replace speaker names with assigned speaker IDs
    import text
    cleaned_new_annos = []
    for i, line in enumerate(new_annos):
        path, speaker, txt = line.split("|")
        if len(txt) > 150:
            continue
        cleaned_text = text._clean_text(txt.replace("[FR]", ""), hps['data']['text_cleaners'])
        cleaned_text += "\n" if not cleaned_text.endswith("\n") else ""
        cleaned_new_annos.append(path + "|" + str(speaker2id[speaker]) + "|" + cleaned_text)

    final_annos = cleaned_new_annos
    
    if add_auxiliary_data:
        with open("./SIWIS.txt", 'r', encoding='utf-8') as f:
            old_annos = f.readlines()
        filtered_old_annos = [line for line in old_annos]
        old_annos = filtered_old_annos
        speakers.insert(0, "SIWIS")
        num_old_voices = len(old_annos)
        num_new_voices = len(new_annos)
        # balance number of new & old voices
        cc_duplicate = num_old_voices // num_new_voices
        if cc_duplicate == 0:
            cc_duplicate = 1

        speaker2id = {speaker: i for i, speaker in enumerate(speakers)}

        hps['data']["n_speakers"] = len(speakers)
        hps['speakers'] = speaker2id
        
        import text
        cleaned_old_annos = []
        for i, line in enumerate(old_annos):
            path, txt = line.split("|")
            if len(txt) > 150:
                continue
            cleaned_text = text._clean_text(txt, hps['data']['text_cleaners'])
            cleaned_text += "\n" if not cleaned_text.endswith("\n") else ""
            cleaned_old_annos.append(path + "|" + str(speaker2id["SIWIS"]) + "|" + cleaned_text)
        # merge with old annotation
        final_annos = cleaned_old_annos + cc_duplicate * final_annos

    # save modified config
    with open("./configs/finetune_speaker.json", 'w', encoding='utf-8') as f:
        json.dump(hps, f, indent=2)
    # save annotation file
    with open("./final_annotation_train.txt", 'w', encoding='utf-8') as f:
        for line in final_annos:
            f.write(line)
    # save annotation file for validation
    with open("./final_annotation_val.txt", 'w', encoding='utf-8') as f:
        for line in cleaned_new_annos:
            f.write(line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--add_auxiliary_data", type=bool, help="Whether to add extra data as fine-tuning helper")
    parser.add_argument("--languages", default="FR")
    args = parser.parse_args()
    if args.languages == "FR":
        langs = ["[FR]"]
    new_annos = []
    # Source 1: transcribed short audios
    if os.path.exists("short_character_anno.txt"):
        with open("short_character_anno.txt", 'r', encoding='utf-8') as f:
            short_character_anno = f.readlines()
            new_annos += short_character_anno
    # Source 2: transcribed long audio segments
    if os.path.exists("./long_character_anno.txt"):
        with open("./long_character_anno.txt", 'r', encoding='utf-8') as f:
            long_character_anno = f.readlines()
            new_annos += long_character_anno

    # Get all speaker names
    speakers = []
    for line in new_annos:
        path, speaker, text = line.split("|")
        if speaker not in speakers:
            speakers.append(speaker)
    assert (len(speakers) != 0), "No audio file found. Please check your uploaded file structure."
    # Source 3 (Optional): sampled audios as extra training helpers
    # STEP 1: modify config file
    with open("./configs/finetune_speaker.json", 'r', encoding='utf-8') as f:
        hps = json.load(f)

    # assign ids to new speakers
    speaker2id = {}
    for i, speaker in enumerate(speakers):
        speaker2id[speaker] = i
    # modify n_speakers
    hps['data']["n_speakers"] = len(speakers)
    # overwrite speaker names
    hps['speakers'] = speaker2id
    hps['train']['log_interval'] = 10
    hps['train']['eval_interval'] = 100
    hps['train']['batch_size'] = 16
    hps['data']['training_files'] = "final_annotation_train.txt"
    hps['data']['validation_files'] = "final_annotation_val.txt"

    # STEP 2: clean annotations, replace speaker names with assigned speaker IDs
    import text
    cleaned_new_annos = []
    for i, line in enumerate(new_annos):
        path, speaker, txt = line.split("|")
        if len(txt) > 150:
            continue
        cleaned_text = text._clean_text(txt.replace("[FR]", ""), hps['data']['text_cleaners'])
        cleaned_text += "\n" if not cleaned_text.endswith("\n") else ""
        cleaned_new_annos.append(path + "|" + str(speaker2id[speaker]) + "|" + cleaned_text)

    final_annos = cleaned_new_annos
    
    if args.add_auxiliary_data:
        with open("./SIWIS.txt", 'r', encoding='utf-8') as f:
            old_annos = f.readlines()
        filtered_old_annos = []
        for line in old_annos:
            filtered_old_annos.append(line)
        old_annos = filtered_old_annos
        for line in old_annos:
            path, text = line.split("|")
            if "SIWIS" not in speakers:
                speakers.insert(0, "SIWIS")
        num_old_voices = len(old_annos)
        num_new_voices = len(new_annos)
        # STEP 1: balance number of new & old voices
        cc_duplicate = num_old_voices // num_new_voices
        if cc_duplicate == 0:
            cc_duplicate = 1

        for i, speaker in enumerate(speakers):
            speaker2id[speaker] = i
        # modify n_speakers
        hps['data']["n_speakers"] = len(speakers)
        # overwrite speaker names
        hps['speakers'] = speaker2id
        
        # STEP 3: clean annotations, replace speaker names with assigned speaker IDs
        import text
        cleaned_old_annos = []
        for i, line in enumerate(old_annos):
            path, txt = line.split("|")
            if len(txt) > 150:
                continue
            cleaned_text = text._clean_text(txt, hps['data']['text_cleaners'])
            cleaned_text += "\n" if not cleaned_text.endswith("\n") else ""
            cleaned_old_annos.append(path + "|" + str(speaker2id["SIWIS"]) + "|" + cleaned_text)
        # merge with old annotation
        final_annos = cleaned_old_annos + cc_duplicate * final_annos
        
    # save modified config
    with open("./configs/finetune_speaker.json", 'w', encoding='utf-8') as f:
        json.dump(hps, f, indent=2)
    # save annotation file
    with open("./final_annotation_train.txt", 'w', encoding='utf-8') as f:
        for line in final_annos:
            f.write(line)
    # save annotation file for validation
    with open("./final_annotation_val.txt", 'w', encoding='utf-8') as f:
        for line in cleaned_new_annos:
            f.write(line)
    print("finished")
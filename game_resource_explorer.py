import pandas as pd
import numpy as np
import re
import io
import os
import h5py
import json
from tqdm import tqdm

# DEBUG
import matplotlib.pyplot as plt
import librosa
import simpleaudio as sa

GAME_DESCRIPTION_FILENAME = 'game.json'
HDF5_KEY_AUDIO_FOLDER = 'audio'
HDF5_KEY_VOICE_BGV_FOLDER = 'voice_bgv'


class GameResourceExplorer:

    """
    This class is designed to act like a library index to read all the data
    stored in all .hdf5 packed games in a folder. I'm not sure how this will
    develop over time, but for now, I can keep all "getters" from this one class.
    """


    def __init__(self):
        pass

    def scan(self, hdf5_directory: str):

        # Stage 1) List all .hdf5 files in the directory
        hdf5_fpaths = [os.path.join(hdf5_directory, filename) for filename in os.listdir(hdf5_directory)]
        game_hdf5_fpaths = [fpath for fpath in hdf5_fpaths if os.path.basename(fpath).startswith('game_')]

        # Stage 2) Get all details
        description_list = []
        for fpath in tqdm(game_hdf5_fpaths):
            description_list.append(self.get_game_details_dict(hdf5_fpath=fpath))
        all_games_df = pd.DataFrame(description_list)
        all_games_df.to_csv('games.csv')

        g = 0

    def get_game_details_dict(self, hdf5_fpath: str) -> dict:

        with h5py.File(hdf5_fpath, 'r', swmr=True) as h5_file:

            # Look for game description
            if GAME_DESCRIPTION_FILENAME not in h5_file:
                return {}

            h5_raw_data = np.void(h5_file[GAME_DESCRIPTION_FILENAME])
            game_dict = json.loads(h5_raw_data.tobytes())
            return {
                    "hdf5_fpath": hdf5_fpath,
                    "title_english": game_dict['title']['english'] if 'english' in game_dict['title'] else '',
                    "title_romanji": game_dict['title']['romanji'] if 'romanji' in game_dict['title'] else '',
                    "title_japanese": game_dict['title']['japanese'] if 'japanese' in game_dict['title'] else '',
                    "release_date": f"{game_dict['release_date']['year']}_{game_dict['release_date']['month']}_{game_dict['release_date']['day']}",
                    "description": game_dict['description'] if 'description' in game_dict else '',
                    "notes": '\n'.join(game_dict['notes']) if 'notes' in game_dict else ''
                }

    def get_game_audio_file_list(self, hdf5_fpath: str):

        stored_audio_files = {}
        with h5py.File(hdf5_fpath, 'r', swmr=True) as h5_file:
            if HDF5_KEY_AUDIO_FOLDER in h5_file:
                for key in h5_file[HDF5_KEY_AUDIO_FOLDER].keys():
                    subitems = list(h5_file[HDF5_KEY_AUDIO_FOLDER][key].keys())
                    stored_files = [f'{HDF5_KEY_AUDIO_FOLDER}/{key}/{item}'for item in subitems]
                    if 'se' in key:
                        stored_audio_files['se'] = stored_files
                    if 'bgv' in key:
                        stored_audio_files['bgv'] = stored_files


        return stored_audio_files

    def get_audio_data(self, hdf5_fpath: str, audio_file: str) -> [np.array, int]:

        with h5py.File(hdf5_fpath, 'r', swmr=True) as h5_file:
            raw_bytes = np.void(h5_file[audio_file]).tobytes()
            samples, sampling_freq = librosa.load(io.BytesIO(raw_bytes))
            return samples, sampling_freq

# DEBUG
if __name__ == "__main__":

    explorer = GameResourceExplorer()
    #explorer.scan("D:\game_resource_archive_hdf5")
    hdf5_fpath = "D:\game_resource_archive_hdf5\game_0039.hdf5"
    audio_files = explorer.get_game_audio_file_list(hdf5_fpath=hdf5_fpath)
    samples, freq = explorer.get_audio_data(hdf5_fpath=hdf5_fpath, audio_file=audio_files['bgv'][2])
    plt.plot(samples)
    plt.show()

    samples_int = (samples * 2**15).astype(np.int16)

    play_obj = sa.play_buffer(samples_int, 1, 2, freq)
    # Wait for playback to finish before exiting
    play_obj.wait_done()

    g = 0

import numpy as np
import sounddevice as sd
import mido
import time

#ZONES
zone1 = [36,40]
zone2 = [37,41]
zone3 = [38,42]
zone4 = [39,43]
zone5 = [44,48]
zone6 = [45,49]
zone7 = [46,50]
zone8 = [47,51]

pad_notes = zone1 + zone2 + zone3 + zone4 + zone5 + zone6 + zone7 + zone8

last_num_pads_on = -1
last_states = [False] * len(pad_notes)
HYSTERESIS = 1

output_name = "MIDIOUT2 (Launchkey MIDI) 2"
outport = mido.open_output(output_name)

DEVICE_INDEX = 34

pad_notes = list(range(36, 52))



#COLORS
zone_colors = {
    "zone1": 43,
    "zone2": 42,
    "zone3": 41,
    "zone4": 50,
    "zone5": 49,
    "zone6": 52,
    "zone7": 54,
    "zone8": 53
}

def clear_pads():
    for note in pad_notes:
        outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))



last_states = [False] * len(pad_notes)

def update_pads_from_volume(vol_norm):
    global last_num_pads_on
    num_pads_on = int(vol_norm * len(pad_notes))

    if abs(num_pads_on - last_num_pads_on) < HYSTERESIS:
        return

    last_num_pads_on = num_pads_on

    for i, note in enumerate(pad_notes):
        should_be_on = i < num_pads_on

        if should_be_on != last_states[i]:
            if should_be_on:
                if note in zone1:
                    color = zone_colors["zone1"]
                elif note in zone2:
                    color = zone_colors["zone2"]
                elif note in zone3:
                    color = zone_colors["zone3"]
                elif note in zone4:
                    color = zone_colors["zone4"]
                elif note in zone5:
                    color = zone_colors["zone5"]
                elif note in zone6:
                    color = zone_colors["zone6"]
                elif note in zone7:
                    color = zone_colors["zone7"]
                else:
                    color = zone_colors["zone8"]
                outport.send(mido.Message('note_on', note=note, velocity=color, channel=15))
            else:
                outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))
            last_states[i] = should_be_on



def get_rms(indata):
    return np.sqrt(np.mean(indata**2))

print("🎧)) Ctrl+C for Exit")
try:
    def callback(indata, frames, time_info, status):
        rms = get_rms(indata)
        vol_norm = min(rms * 5, 1.0)
        update_pads_from_volume(vol_norm)

    with sd.InputStream(device=DEVICE_INDEX, callback=callback,
                        channels=2, samplerate=44100, dtype='float32'):
        while True:
            time.sleep(0.05)

except KeyboardInterrupt:
    print("🛑")
    clear_pads()
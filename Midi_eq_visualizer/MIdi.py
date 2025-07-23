import numpy as np
import sounddevice as sd
import mido
import time
import threading  # 🔧 Додано!

# Silence Animation
class SilenceWaveAnimator:
    def __init__(self, pads, outport, colors, interval=0.1):
        self.pads = pads
        self.outport = outport
        self.colors = colors
        self.interval = interval
        self.active = False
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.position = 0

    def start(self):
        self.active = True
        if not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.active = False
        self.clear()

    def clear(self):
        for note in self.pads:
            self.outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))

    def run(self):
        while True:
            if not self.active:
                time.sleep(self.interval)
                continue

            for i, note in enumerate(self.pads):
                distance = abs(i - self.position)
                if distance == 0:
                    vel = self.colors[4]
                elif distance == 1:
                    vel = self.colors[3]
                elif distance == 2:
                    vel = self.colors[2]
                elif distance == 3:
                    vel = self.colors[1]
                elif distance == 4:
                    vel = self.colors[0]
                else:
                    vel = 0

                if vel > 0:
                    self.outport.send(mido.Message('note_on', note=note, velocity=vel, channel=15))
                else:
                    self.outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))

            self.position = (self.position + 1) % len(self.pads)
            time.sleep(self.interval)


# 🎛 Zones
zone1 = [36,40]
zone2 = [37,41]
zone3 = [38,42]
zone4 = [39,43]
zone5 = [44,48]
zone6 = [45,49]
zone7 = [46,50]
zone8 = [47,51]
pad_notes = zone1 + zone2 + zone3 + zone4 + zone5 + zone6 + zone7 + zone8

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

output_name = "MIDIOUT2 (Launchkey MIDI) 2"
outport = mido.open_output(output_name)
DEVICE_INDEX = 34
HYSTERESIS = 1

last_num_pads_on = -1
last_states = [False] * len(pad_notes)

def clear_pads():
    for note in pad_notes:
        outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))

def get_rms(indata):
    return np.sqrt(np.mean(indata**2))

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
                # Optimization
                for z_idx, zone in enumerate([zone1, zone2, zone3, zone4, zone5, zone6, zone7, zone8], start=1):
                    if note in zone:
                        color = zone_colors[f"zone{z_idx}"]
                        break
                outport.send(mido.Message('note_on', note=note, velocity=color, channel=15))
            else:
                outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))

            last_states[i] = should_be_on


# Wave init
wave = SilenceWaveAnimator(
    pads=pad_notes,
    outport=outport,
    colors=[41,42,43,38,39],
    interval=0.08
)

#Start
print("🎧 Ctrl+C to Exit")
try:
    def callback(indata, frames, time_info, status):
        rms = get_rms(indata)
        vol_norm = min(rms * 5, 1.0)
        total_vol = vol_norm  # 🔧 Просто total_vol = rms * 5

        if total_vol < 0.03:
            if not wave.active:
                wave.start()
        else:
            if wave.active:
                wave.stop()
            update_pads_from_volume(vol_norm)

    with sd.InputStream(device=DEVICE_INDEX, callback=callback,
                        channels=2, samplerate=44100, dtype='float32'):
        while True:
            time.sleep(0.05)

except KeyboardInterrupt:
    print("🛑")
    clear_pads()
    wave.stop()

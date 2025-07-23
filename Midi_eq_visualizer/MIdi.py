import numpy as np
import sounddevice as sd
import mido
import time
import threading

# ==== Silence Animation ====
class RowWaveAnimator:
    def __init__(self, top_pads, bottom_pads, outport, color_range=(40, 60), interval=0.1):
        self.top_pads = top_pads
        self.bottom_pads = bottom_pads
        self.outport = outport
        self.color_range = color_range
        self.interval = interval
        self.active = False
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.state = "top"
        self.direction = 1
        self.color_value = color_range[0]

    def start(self):
        self.active = True
        if not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.active = False
        self.clear()

    def clear(self):
        for note in self.top_pads + self.bottom_pads:
            self.outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))

    def run(self):
        while True:
            if not self.active:
                time.sleep(0.1)
                continue

            pads = self.top_pads if self.state == "top" else self.bottom_pads

            for note in pads:
                self.outport.send(mido.Message('note_on', note=note, velocity=int(self.color_value), channel=15))
                time.sleep(self.interval)
                self.outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))

            self.color_value += self.direction
            if self.color_value >= self.color_range[1] or self.color_value <= self.color_range[0]:
                self.direction *= -1

            self.state = "bottom" if self.state == "top" else "top"


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
                vel = self.colors[distance] if distance < len(self.colors) else 0

                msg_type = 'note_on' if vel > 0 else 'note_off'
                self.outport.send(mido.Message(msg_type, note=note, velocity=vel, channel=15))

            self.position = (self.position + 1) % len(self.pads)
            time.sleep(self.interval)


# ==== Config ====

output_name = "MIDIOUT2 (Launchkey MIDI) 2"
DEVICE_INDEX = 34
HYSTERESIS = 1

zones = [
    [36, 40], [37, 41], [38, 42], [39, 43],
    [44, 48], [45, 49], [46, 50], [47, 51]
]

zone_colors_list = [43, 42, 41, 50, 49, 52, 54, 53]

pad_notes = [note for zone in zones for note in zone]

# ==== MIDI ====

outport = mido.open_output(output_name)

def clear_pads():
    for note in pad_notes:
        outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))

# ==== Volume logic ====

last_num_pads_on = -1
last_states = [False] * len(pad_notes)

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
                for zone_index, zone in enumerate(zones):
                    if note in zone:
                        color = zone_colors_list[zone_index]
                        break
                outport.send(mido.Message('note_on', note=note, velocity=color, channel=15))
            else:
                outport.send(mido.Message('note_off', note=note, velocity=0, channel=15))

            last_states[i] = should_be_on

# ==== Silence Animation ====
top_row = [36, 37, 38, 39, 44, 45, 46, 47]
bottom_row = [40, 41, 42, 43, 48, 49, 50, 51]

wave = RowWaveAnimator(
    top_pads=top_row,
    bottom_pads=bottom_row,
    outport=outport,
    color_range=(40, 60),
    interval=0.08)

# wave = SilenceWaveAnimator(
#     pads=pad_notes,
#     outport=outport,
#     colors=[41, 42, 43, 38, 39],
#     interval=0.08
# )

# ==== Audio Callback ====

print("🎧 Ctrl+C to Exit")
try:
    def callback(indata, frames, time_info, status):
        rms = get_rms(indata)
        vol_norm = min(rms * 5, 1.0)

        if vol_norm < 0.03:
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

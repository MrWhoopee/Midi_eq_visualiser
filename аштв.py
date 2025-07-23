import mido
import time

output_name = "MIDIOUT2 (Launchkey MIDI) 2"
outport = mido.open_output(output_name)

pad_notes = list(range(36, 52))
velocity_color = 52  # Вибери колір: 52 = фіолетовий

# Стан педів (щоб не посилати повторно)
pad_state = {note: False for note in pad_notes}

def light_up_pads():
    for note in pad_notes:
        if not pad_state[note]:
            outport.send(mido.Message('note_on', note=note, velocity=velocity_color, channel=1))
            pad_state[note] = True

def clear_pads():
    for note in pad_notes:
        outport.send(mido.Message('note_off', note=note, velocity=0, channel=1))
        pad_state[note] = False

print("✨ Педи увімкнені один раз. Ctrl+C — вихід.")

try:
    light_up_pads()
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Вимикаю педи...")
    clear_pads()
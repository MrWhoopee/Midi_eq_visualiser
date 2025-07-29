import sounddevice as sd

for i, dev in enumerate(sd.query_devices()):
    print(f"{i}: {dev['name']}  ({dev['max_input_channels']} in / {dev['max_output_channels']} out)")
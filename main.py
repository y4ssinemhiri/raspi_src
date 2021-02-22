import mido
import numpy as np
import sounddevice as sd 


fs = 44100
t = 1
n = np.arange(t*fs)

def midi_callback(msg):

    if msg.type == "note_on":
        channel, note, velocity = msg.bytes()
        f = 2**((note-69)/12) * 440
        buff = np.sin(2*np.pi*f*n/fs)
    #     sd.play(buff, fs)

    def callback(indata, outdata, frames, times, status):
        outdata[:] += buff
    
    with sd.Stream(channels=2, callback=callback):
        sd.sleep(int(1))
            
    return True


with mido.open_input("Steinberg UR242 MIDI 1") as inport:
    for msg in inport:
        midi_callback(msg)
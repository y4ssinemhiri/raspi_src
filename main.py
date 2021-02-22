import mido
import numpy as np
import sounddevice as sd 


fs = 44100
t = 1
n = np.arange(t*fs)

def callback(msg):

    if msg.type == "note_on":
        channel, note, velocity = msg.bytes()
        f = 2**((note-69)/12) * 440
        buff = np.sin(2*np.pi*f*n/fs)
        sd.play(buff, fs)
    
    return True


with mido.open_input() as inport:
    for msg in inport:
        callback(msg)
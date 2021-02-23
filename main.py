import mido
import asyncio
import numpy as np
import sounddevice as sd 


fs = 44100
t = 1
n = np.arange(t*fs)


async def play_note(midi_msg, **kwargs):
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    idx = 0


    channel, note, velocity = midi_msg.bytes()
    f = 2**((note-69)/12) * 440
    buffer = np.sin(2*np.pi*f*n/fs)

    def callback(outdata, frame_count, time_info, status):
        nonlocal idx
        if status:
            print(status)
        remainder = len(buffer) - idx
        if remainder == 0:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        valid_frames = frame_count if remainder >= frame_count else remainder
        outdata[:valid_frames] = buffer[idx:idx + valid_frames]
        outdata[valid_frames:] = 0
        idx += valid_frames

    stream = sd.OutputStream(callback=callback, dtype=buffer.dtype,
                             channels=buffer.shape[1], **kwargs)
    with stream:
        await event.wait()


async def wait_for_midi_input(midi_msg):

    loop = asyncio.get_event_loop()
    event = asyncio.Event()

    with mido.open_input("Steinberg UR242 MIDI 1") as inport: 
        if msg in inport and msg.types == "note_on":
            midi_msg = msg
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop 

        await event.wait()     
        
            

asyncio def main():

    midi_msg = 0
    await wait_for_midi_input(midi_msg)

    await play_note(midi_msg)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')






    

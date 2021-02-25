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
    buffer = np.reshape(buffer, (-1,1)).astype(np.float32)

    def callback(outdata, frame_count, time_info, status):
        nonlocal idx
        print("here")
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

def make_stream():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()
    def callback(message):
        loop.call_soon_threadsafe(queue.put_nowait, message)
    async def stream():
        while True:
            yield await queue.get()
    return callback, stream()

async def print_messages():
    # create a callback/stream pair and pass callback to mido
    cb, stream = make_stream()
    mido.open_input("Steinberg UR242 MIDI 1", callback=cb)

    # print messages as they come just by reading from stream
    async for message in stream:
        print(message)

async def get_midi_input(midi_msg):

    loop = asyncio.get_event_loop()
    event = asyncio.Event()

    with mido.open_input("Steinberg UR242 MIDI 1") as inport:
        print("waiting for msg")
        while True:
            for msg in inport.iter_pending():
                print(msg)
                if msg.type == "note_on":
                    print("HERE")
                    return msg
            
async def midi_event():
    midi_msg = await wait_for_midi_input(midi_msg)
    await play_note(midi_msg)

async def main():

    midi_task = asyncio.create_task(midi_event())

    while True:
        await print_messages()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')






    

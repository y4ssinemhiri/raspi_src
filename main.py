import mido
import asyncio
import numpy as np
import sounddevice as sd 


fs = 44100
t = 1
n = np.arange(t*fs)


async def play_note(queue, **kwargs):
    while True:
        loop = asyncio.get_event_loop() 
        event = asyncio.Event()
        idx = 0
        msg = await queue.get()
        print("msg receveid", msg)

        channel, note, velocity = msg.bytes()
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

async def get_midi_input(queue):

    with mido.open_input("Steinberg UR242 MIDI 1") as inport:
        print("waiting for msg")
        while True:
#            print("input")
            for msg in inport.iter_pending():
                if msg.type == "note_on":
                    print(msg)
                    await queue.put(msg)
            await asyncio.sleep(0.001)


async def midi_event():
    await get_midi_input()
    #await play_note(midi_msg)

async def main():
    midi_queue = asyncio.Queue()

    midi_task = get_midi_input(midi_queue)
#    play_note_task = asyncio.ensure_future(play_note(midi_queue))

#    with mido.open_input("Steinberg UR242 MIDI 1") as inport:
#        print("waiting for msg")
#        while True:
#            for msg in inport.iter_pending():
#                print(msg)
#                await midi_queue.put(msg)
#            print("test")
    await asyncio.gather(*[midi_task, play_note(midi_queue)])
    await midi_queue.join()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')






    

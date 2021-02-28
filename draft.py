
import mido
import asyncio
import numpy as np
import sounddevice as sd 
import queue
import time

async def stream_generator(blocksize, *, channels=1, dtype='float32',
                           pre_fill_blocks=10, **kwargs):
    """Generator that yields blocks of input/output data as NumPy arrays.

    The output blocks are uninitialized and have to be filled with
    appropriate audio signals.

    """
    assert blocksize != 0
    q_in = asyncio.Queue()
    q_out = queue.Queue()
    loop = asyncio.get_event_loop()

    def callback(indata, outdata, frame_count, time, status):
        loop.call_soon_threadsafe(q_in.put_nowait, (indata.copy(), status))
        outdata[:] = q_out.get_nowait()

    # pre-fill output queue
    for _ in range(pre_fill_blocks):
        q_out.put(np.zeros((blocksize, channels), dtype=dtype))

    stream = sd.Stream(blocksize=blocksize, callback=callback, dtype=dtype,
                       channels=channels, **kwargs) 
    outdata = np.empty((blocksize, channels), dtype=dtype) 
    with stream:
        while True:
            indata, status = await q_in.get()
            yield outdata, status
            q_out.put_nowait(outdata)

async def audio_wire(q_out, **kwargs):
    """Create a connection between audio inputs and outputs.

    Asynchronously iterates over a stream generator and for each block
    simply copies the input data into the output block.

    """
    print("here")
    async for outdata,status in stream_generator(blocksize=4096):
        if status:
            print(status)
        try:
            outdata[:] = q_out.get_nowait()
        except asyncio.QueueEmpty:
            outdata[:] = np.zeros((4096,1))



async def midi_stream_generator():

    loop = asyncio.get_event_loop()
    q_in = queue.Queue()

    def callback(message):
        if message.type == "note_on":
            loop.call_soon_threadsafe(q_in.put_nowait, (message))


    port =  mido.open_input("Steinberg UR242 MIDI 1", callback=callback)
    while True:
        msg = await q_in.get()
        yield msg
        print("message receveid", msg)



async def send_to_audio_stream(q_out, q_midi, blocksize=4096):

    while True:
        data = yield from midi_consumer(q_midi)

        n_channel, n_frames = data.shape[1], data.shape[0] // blocksize  +  1 * (data.shape[0] % blocksize != 0)

        outdata = np.empty((n_frames, blocksize, n_channel))
        idx = 0
        for frame  in range(n_frames):
            remainder = len(data) - idx
            if remainder > 0:
                valid_frames = blocksize if remainder >= blocksize else remainder
                outdata[frame, :valid_frames] = data[idx:idx + valid_frames]
                outdata[frame, valid_frames:] = 0
                idx += valid_frames
                yield from q_out.put(outdata[frame])


async def midi_listener(q_midi, blocksize=4096):

    asyncio.ensure_future(consumer(q_midi))
    while True:
        msg = yield from midi_stream_generator()
        if msg:
            yield from q_midi.put(msg)

async def midi_consumer(q_midi):
    
    event = asyncio.Event()
    message = None

    while True:
        try:
            message =  await q_midi.get_nowait()
        except asyncio.QueueEmpty:
            pass
            
        if message is not None:
            if msg.type == "note_on":
                await event.set()

            if msg.type == "note_off":
                await event.clear()

            if event.is_set():
                channel, note, velocity = msg.bytes()
                f = 2**((note-69)/12) * 440
                    
                fs = 44100
                period = fs/f 
                t = (blocksize // period) * period 
                n = np.arange(t)
                audio_data = 0.1*np.sin(2*np.pi*f*n/fs)
                audio_data = np.reshape(audio_data, (-1,1)).astype(np.float32) 
                
                yield from q_out.put(audio_data) 
    

async def main():

    q_midi = asyncio.Queue()
    q_out = asyncio.Queue()

    open_audio_stream = asyncio.create_task(audio_wire(q_out))
    open_midi_stream = asyncio.create_task(midi_listener(q_midi))
    await asyncio.gather(*[open_audio_stream, open_midi_stream, send_to_audio_stream(q_out, q_midi)])
    
    await open_midi_stream
    await open_audio_stream


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')




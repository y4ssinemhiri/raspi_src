
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
    async for outdata, status in stream_generator(**kwargs):
        if status:
            print(status)
        try:
            data = q_out.get_nowait()
            q_out.task_done()
            outdata[:] = data
        except asyncio.QueueEmpty:
            outdata[:] = np.zeros((blocksize,1))



async def midi_stream_generator():
   
    loop = asyncio.get_event_loop()
    q_in = asyncio.Queue()

    def callback(message): 
        loop.call_soon_threadsafe(q_in.put_nowait, (message))


    port =  mido.open_input("Steinberg UR242 MIDI 1", callback=callback)
    while True:
        print("in midi_stream_generator")
        #try:
        msg = await q_in.get()
        yield msg
        print("message receveid", msg)


async def midi_listener(q_midi, event, **kwargs):
    loop = asyncio.get_event_loop()

    while True:
        print("in midi_listener")
        async for msg in midi_stream_generator():
            print("in midi_listener")
            q_midi.put_nowait(msg)
            print("waiting for midi msg")
            if msg is not None:
                if msg.type == "note_on":
                    loop.call_soon_threadsafe(event.set)

                if msg.type == "note_off":
                    print("here")
                    loop.call_soon_threadsafe(event.clear)


async def midi_consumer(q_midi, q_out, event, **kwargs):
    
    t0 = 0
    while True:
        print(event.is_set())
        await event.wait()
        try:
            msg = q_midi.get_nowait()
        except asyncio.QueueEmpty:
            pass
            
        channel, note, velocity = msg.bytes()
        f = 2**((note-69)/12) * 440
        fs = 44100 
        period = blocksize
        t =  (blocksize // period) * period 
        n = np.arange(t0, t0 + t)
        t0 = n[-1]
        audio_data = 0.1*np.sin(2*np.pi*f*n/fs)
        audio_data = np.reshape(audio_data, (-1,1)).astype(np.float32)   
        q_out.put_nowait(audio_data)
        await asyncio.sleep(blocksize/fs)

async def main(**kwargs):

    event = asyncio.Event()
    event.clear()
    q_midi = asyncio.Queue()
    q_out = asyncio.Queue()

    open_audio_stream = asyncio.create_task(audio_wire(q_out))
    open_midi_stream = asyncio.create_task(midi_listener(q_midi, event))
    instrument = asyncio.create_task(midi_consumer(q_midi, q_out, event))
    await asyncio.gather(*[open_audio_stream, open_midi_stream, instrument])

    await send_audio_task
    await open_midi_stream
    await open_audio_stream


if __name__ == "__main__":
    try:
        asyncio.run(main(blocksize=512))
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')




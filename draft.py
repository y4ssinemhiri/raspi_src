
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
    event = asyncio.Event()

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


async def update_buffer(q_out, **kwargs):
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

async def midi_stream_generator(q_out):

    q_in = asyncio.Queue()
    loop = asyncio.get_event_loop()
    def callback(message):
        if message.type == "note_on":
            loop.call_soon_threadsafe(q_in.put_nowait, (message))
            print("from callback", message)

    port =  mido.open_input("Steinberg UR242 MIDI 1", callback=callback)
    while True:
        msg = await q_in.get()
        print("message receveid", msg)
        await singer(q_out, msg)
        print("message processed")


async def send_to_audio_stream(q_out, data, blocksize):

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
            q_out.put_nowait(outdata[frame])




async def singer(q_out, msg):

    fs = 44100
    t = 0.1 
    n = np.arange(t*fs)
    channel, note, velocity = msg.bytes()
    f = 2**((note-69)/12) * 440
    audio_data = 0.1*np.sin(2*np.pi*f*n/fs)
    audio_data = np.reshape(audio_data, (-1,1)).astype(np.float32)    

    await send_to_audio_stream(q_out, audio_data, blocksize=4096)



async def main():

    q_out = asyncio.Queue()
    audio_task = asyncio.create_task(update_buffer(q_out))
    await midi_stream_generator(q_out)
#    await asyncio.gather(*[audio_task, midi_stream_generator(q_out)])
    await audio_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')




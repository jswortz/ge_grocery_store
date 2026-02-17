/**
 * PCM Audio Playback Processor for Web Audio API.
 *
 * Runs on the audio rendering thread via AudioWorklet for low-latency
 * playback of 16-bit PCM audio streamed from the ADK Live API (24kHz).
 *
 * Based on ADK streaming best practices:
 * https://google.github.io/adk-docs/streaming/dev-guide/part5/
 */
class PCMPlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();

    // Ring buffer: 10 seconds at 24kHz
    this.bufferSize = 24000 * 10;
    this.buffer = new Float32Array(this.bufferSize);
    this.readIndex = 0;
    this.writeIndex = 0;

    // Listen for audio data and control messages from the main thread
    this.port.onmessage = (event) => {
      if (event.data.command === 'endOfAudio') {
        // Clear buffer on interruption or turn end
        this.readIndex = this.writeIndex;
        return;
      }

      if (event.data.command === 'clear') {
        this.readIndex = 0;
        this.writeIndex = 0;
        this.buffer.fill(0);
        return;
      }

      // Incoming data is an ArrayBuffer of 16-bit PCM samples
      const int16Samples = new Int16Array(event.data);
      this._enqueue(int16Samples);
    };
  }

  /**
   * Push incoming Int16 PCM data into the ring buffer.
   * Converts 16-bit integer samples to Float32 [-1.0, 1.0].
   */
  _enqueue(int16Samples) {
    for (let i = 0; i < int16Samples.length; i++) {
      // Convert 16-bit integer to float [-1.0, 1.0]
      const floatVal = int16Samples[i] / 32768;

      this.buffer[this.writeIndex] = floatVal;
      this.writeIndex = (this.writeIndex + 1) % this.bufferSize;

      // Overflow: if write catches up to read, advance read (drop oldest)
      if (this.writeIndex === this.readIndex) {
        this.readIndex = (this.readIndex + 1) % this.bufferSize;
      }
    }
  }

  /**
   * Called by Web Audio system ~128 samples at a time.
   * Outputs mono→stereo PCM from the ring buffer.
   */
  process(inputs, outputs, parameters) {
    const output = outputs[0];
    const framesPerBlock = output[0].length;

    for (let frame = 0; frame < framesPerBlock; frame++) {
      // Read from ring buffer
      const sample = this.buffer[this.readIndex];
      output[0][frame] = sample; // left channel

      // Duplicate mono to stereo if stereo output
      if (output.length > 1) {
        output[1][frame] = sample; // right channel
      }

      // Advance read index unless buffer is empty (underflow → silence)
      if (this.readIndex !== this.writeIndex) {
        this.readIndex = (this.readIndex + 1) % this.bufferSize;
      }
    }

    return true; // Keep processor alive
  }
}

registerProcessor('pcm-player-processor', PCMPlayerProcessor);

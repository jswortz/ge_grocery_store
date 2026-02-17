/**
 * PCM Audio Recorder Processor for Web Audio API.
 *
 * Runs on the audio rendering thread via AudioWorklet for low-latency
 * microphone capture. Copies Float32 samples from the mic input and
 * posts them to the main thread for conversion to 16-bit PCM.
 */
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
  }

  process(inputs, outputs, parameters) {
    if (inputs.length > 0 && inputs[0].length > 0) {
      const inputChannel = inputs[0][0];
      // Copy the buffer to avoid issues with recycled memory
      const inputCopy = new Float32Array(inputChannel);
      this.port.postMessage(inputCopy);
    }
    return true;
  }
}

registerProcessor('pcm-recorder-processor', PCMProcessor);

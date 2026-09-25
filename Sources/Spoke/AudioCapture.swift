import AVFoundation

/// Captura el micrófono, lo convierte a 16 kHz mono y lo agrupa en
/// "enunciados" (voz entre pausas). Mientras hablás entrega el audio parcial
/// del enunciado en curso por `onPartial` cada `partialIntervalMs`, y al detectar
/// la pausa entrega el enunciado completo por `onUtterance`. Ambos callbacks
/// llevan el id del enunciado y se llaman desde la cola de audio.
final class AudioCapture {
    var onPartial: ((Int, [Float]) -> Void)?
    var onUtterance: ((Int, [Float]) -> Void)?
    var onLevel: ((Float) -> Void)?   // 0…1, para la onda del HUD

    private let engine = AVAudioEngine()
    private let queue = DispatchQueue(label: "spoke.audio", qos: .userInitiated)
    private var converter: AVAudioConverter?
    private let outFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                          sampleRate: Config.sampleRate, channels: 1, interleaved: false)!

    // Estado del segmentador (sólo se toca desde `queue`)
    private let frameLen = Int(Config.sampleRate * Config.frameMs / 1000)
    private var pending: [Float] = []        // muestras aún no agrupadas en frames
    private var preRoll: [Float] = []
    private var segment: [Float] = []
    private var inSpeech = false
    private var speechFrames = 0
    private var silenceFrames = 0
    private var samplesSincePartial = 0
    private var utteranceId = 0
    private var recentRMS: [Float] = []      // ventana para estimar el ruido de fondo

    func start() throws {
        queue.sync { resetSegmenter() }
        let input = engine.inputNode
        let inFormat = input.outputFormat(forBus: 0)
        converter = AVAudioConverter(from: inFormat, to: outFormat)

        input.installTap(onBus: 0, bufferSize: 1024, format: inFormat) { [weak self] buffer, _ in
            guard let self, let samples = self.convert(buffer) else { return }
            self.queue.async { self.consume(samples) }
        }
        engine.prepare()
        try engine.start()
    }

    /// Detiene la captura, entrega el enunciado en curso y luego llama a
    /// `completion` en main (después de ese `onUtterance`).
    func stop(completion: @escaping () -> Void) {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        queue.async {
            if self.inSpeech { self.endUtterance() }
            self.resetSegmenter()
            DispatchQueue.main.async(execute: completion)
        }
    }

    /// Modo prueba: reproduce un archivo en tiempo real a través del mismo
    /// segmentador que el micrófono.
    func feed(file url: URL, completion: @escaping () -> Void) throws {
        let file = try AVAudioFile(forReading: url)
        converter = AVAudioConverter(from: file.processingFormat, to: outFormat)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat,
                                            frameCapacity: AVAudioFrameCount(file.length)) else { return }
        try file.read(into: buffer)
        guard let samples = convert(buffer) else { return }
        let chunk = Int(Config.sampleRate / 10) // 100 ms
        queue.async { self.resetSegmenter() }
        for (i, start) in stride(from: 0, to: samples.count, by: chunk).enumerated() {
            let piece = Array(samples[start..<min(start + chunk, samples.count)])
            queue.asyncAfter(deadline: .now() + .milliseconds(100 * i)) { self.consume(piece) }
        }
        let total = (samples.count / chunk + 1) * 100
        queue.asyncAfter(deadline: .now() + .milliseconds(total)) {
            if self.inSpeech { self.endUtterance() }
            DispatchQueue.main.async(execute: completion)
        }
    }

    private func convert(_ buffer: AVAudioPCMBuffer) -> [Float]? {
        guard let converter else { return nil }
        let ratio = outFormat.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 64
        guard let out = AVAudioPCMBuffer(pcmFormat: outFormat, frameCapacity: capacity) else { return nil }
        var fed = false
        var error: NSError?
        converter.convert(to: out, error: &error) { _, status in
            if fed { status.pointee = .noDataNow; return nil }
            fed = true
            status.pointee = .haveData
            return buffer
        }
        guard error == nil, let data = out.floatChannelData else { return nil }
        return Array(UnsafeBufferPointer(start: data[0], count: Int(out.frameLength)))
    }

    private func consume(_ samples: [Float]) {
        pending += samples
        while pending.count >= frameLen {
            let frame = Array(pending.prefix(frameLen))
            pending.removeFirst(frameLen)
            process(frame)
        }
    }

    /// Ruido de fondo = el frame más bajo de los últimos ~3 s. Se sigue
    /// adaptando aunque haya ruido constante (ventilador, aire, etc.).
    private func speechThreshold(_ rms: Float) -> Float {
        recentRMS.append(rms)
        if recentRMS.count > 100 { recentRMS.removeFirst() }
        let floor = recentRMS.min() ?? rms
        return max(floor * 3, 0.006)
    }

    private func process(_ frame: [Float]) {
        let rms = sqrt(frame.reduce(0) { $0 + $1 * $1 } / Float(frame.count))
        let isSpeech = rms > speechThreshold(rms)

        let level = min(1, rms * 12)
        DispatchQueue.main.async { self.onLevel?(level) }

        if inSpeech {
            segment += frame
            samplesSincePartial += frame.count
            if isSpeech { speechFrames += 1; silenceFrames = 0 } else { silenceFrames += 1 }

            let silenceMs = Double(silenceFrames) * Config.frameMs
            let segmentMs = Double(segment.count) / Config.sampleRate * 1000
            if silenceMs >= Config.silenceToCutMs || segmentMs >= Config.maxSegmentMs {
                endUtterance()
            } else if Double(samplesSincePartial) / Config.sampleRate * 1000 >= Config.partialIntervalMs,
                      Double(speechFrames) * Config.frameMs >= Config.minSpeechMs {
                samplesSincePartial = 0
                onPartial?(utteranceId, padded(segment))
            }
        } else {
            preRoll += frame
            let maxPreRoll = Int(Config.sampleRate * Config.preRollMs / 1000)
            if preRoll.count > maxPreRoll { preRoll.removeFirst(preRoll.count - maxPreRoll) }
            if isSpeech {
                inSpeech = true
                segment = preRoll
                preRoll = []
                speechFrames = 1
                silenceFrames = 0
                samplesSincePartial = 0
            }
        }
    }

    private func endUtterance() {
        let speechMs = Double(speechFrames) * Config.frameMs
        // Aunque sea muy corto se entrega vacío: la sesión necesita cerrar el enunciado.
        onUtterance?(utteranceId, speechMs >= Config.minSpeechMs ? padded(segment) : [])
        utteranceId += 1
        segment = []
        inSpeech = false
        speechFrames = 0
        silenceFrames = 0
        samplesSincePartial = 0
    }

    /// Whisper rinde mejor con al menos ~1 s de audio: rellena con silencio.
    private func padded(_ samples: [Float]) -> [Float] {
        let minLen = Int(Config.sampleRate * 1.0)
        return samples.count >= minLen ? samples : samples + [Float](repeating: 0, count: minLen - samples.count)
    }

    private func resetSegmenter() {
        pending = []; preRoll = []; segment = []
        inSpeech = false; speechFrames = 0; silenceFrames = 0; samplesSincePartial = 0
        utteranceId = 0
    }
}

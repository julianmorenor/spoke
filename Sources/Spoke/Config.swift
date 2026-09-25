import Carbon.HIToolbox
import Foundation

enum Config {
    static let modelPath = NSString(string: "~/.local/share/whisper/ggml-large-v3-turbo.bin").expandingTildeInPath
    static let ggmlBackendsPath = "/opt/homebrew/opt/ggml/libexec"
    static let language = "es"

    // Atajo global: ⌥ Space
    static let hotKeyCode = UInt32(kVK_Space)
    static let hotKeyModifiers = UInt32(optionKey)
    static let hotKeyLabel = "⌥ Space"

    // Segmentación (detección de voz por energía)
    static let sampleRate = 16_000.0
    static let frameMs = 30.0
    static let partialIntervalMs = 500.0  // cada cuánto se retranscribe mientras hablás
    static let silenceToCutMs = 500.0     // pausa que cierra un enunciado
    static let minSpeechMs = 250.0        // enunciados más cortos se descartan
    static let maxSegmentMs = 15_000.0    // corte forzado si no hay pausas
    static let preRollMs = 240.0          // audio previo al inicio de voz
}

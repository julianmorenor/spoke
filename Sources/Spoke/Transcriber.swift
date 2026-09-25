import CWhisper
import Foundation

/// Envuelve whisper.cpp. Todas las llamadas corren en una cola serial propia,
/// así los fragmentos se transcriben (y se insertan) en orden.
final class Transcriber {
    private var ctx: OpaquePointer?
    private let queue = DispatchQueue(label: "spoke.whisper", qos: .userInitiated)
    private let language = strdup(Config.language)

    // Frases que Whisper "alucina" sobre silencio o ruido.
    private static let hallucinations: Set<String> = [
        "gracias.", "gracias", "¡gracias!", "gracias por ver el video.", "gracias por ver.",
        "subtítulos realizados por la comunidad de amara.org",
        "subtítulos por la comunidad de amara.org",
        "¡suscríbete!", "suscríbete al canal.", "thank you.", "thanks for watching!",
        "...", ".",
    ]

    func load(completion: @escaping (Bool) -> Void) {
        queue.async {
            whisper_log_set({ _, _, _ in }, nil) // silencia los logs de whisper.cpp
            // El ggml de Homebrew carga Metal/CPU como plugins dinámicos.
            ggml_backend_load_all_from_path(Config.ggmlBackendsPath)
            var cparams = whisper_context_default_params()
            cparams.use_gpu = true
            cparams.flash_attn = true
            self.ctx = whisper_init_from_file_with_params(Config.modelPath, cparams)
            guard self.ctx != nil else { return completion(false) }
            // Calentamiento: compila los shaders de Metal antes del primer dictado.
            _ = self.run(samples: [Float](repeating: 0, count: 16_000), prompt: nil)
            completion(true)
        }
    }

    /// Libera el modelo. Hay que llamarlo antes de salir: si no, el backend
    /// Metal aborta en los destructores estáticos.
    func shutdown() {
        queue.sync {
            if let ctx { whisper_free(ctx) }
            ctx = nil
        }
    }

    /// Transcribe un fragmento en la cola serial y devuelve el texto en main.
    /// `partial`: pasada rápida sobre audio que sigue creciendo (sin reintentos).
    func transcribe(_ samples: [Float], prompt: String?, partial: Bool = false,
                    completion: @escaping (String) -> Void) {
        queue.async {
            let t0 = Date()
            let text = self.run(samples: samples, prompt: prompt, partial: partial)
            if Self.debug {
                print(String(format: "   whisper %@ %.1fs de audio → %.0f ms", partial ? "parcial" : "final",
                             Double(samples.count) / Config.sampleRate, Date().timeIntervalSince(t0) * 1000))
            }
            DispatchQueue.main.async { completion(text) }
        }
    }

    private static let debug = ProcessInfo.processInfo.environment["SPOKE_DEBUG"] != nil

    private func run(samples: [Float], prompt: String?, partial: Bool = false) -> String {
        guard let ctx else { return "" }
        var params = whisper_full_default_params(WHISPER_SAMPLING_GREEDY)
        params.n_threads = Int32(max(1, min(8, ProcessInfo.processInfo.activeProcessorCount - 2)))
        params.language = UnsafePointer(language)
        params.translate = false
        params.no_context = true
        params.no_timestamps = true
        params.single_segment = false
        params.print_special = false
        params.print_progress = false
        params.print_realtime = false
        params.print_timestamps = false
        params.suppress_blank = true
        params.suppress_nst = true
        let seconds = Double(samples.count) / Config.sampleRate
        if partial {
            // Whisper procesa una ventana fija de 30 s. En las parciales usamos
            // la mitad (768 frames ≈ 15 s): ~0.5 s por pasada en vez de ~0.9 s.
            // Ventanas más chicas o ajustadas al audio son más rápidas pero
            // producen basura seguido. La pasada final usa la ventana completa.
            if seconds <= 14 { params.audio_ctx = 768 }
            // Una hipótesis mala no importa: la próxima pasada la corrige.
            // Sin reintentos por temperatura y con tope de tokens (~5/s de voz),
            // así una repetición no puede trabar la cola.
            params.temperature_inc = 0
            params.max_tokens = Int32(seconds * 5 + 8)
        }

        let promptC = prompt.flatMap { strdup($0) }
        defer { free(promptC) }
        params.initial_prompt = UnsafePointer(promptC)

        let status = samples.withUnsafeBufferPointer {
            whisper_full(ctx, params, $0.baseAddress, Int32($0.count))
        }
        guard status == 0 else { return "" }

        var text = ""
        for i in 0..<whisper_full_n_segments(ctx) {
            if whisper_full_get_segment_no_speech_prob(ctx, i) > 0.6 { continue }
            if let cstr = whisper_full_get_segment_text(ctx, i) {
                text += String(cString: cstr)
            }
        }
        text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if Self.hallucinations.contains(text.lowercased()) { return "" }
        return text
    }
}

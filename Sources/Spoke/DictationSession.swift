import Foundation

/// Convierte audio parcial en texto escrito en vivo, sin tener que borrar nunca.
///
/// Mientras hablás, cada pasada de Whisper sobre el enunciado en curso da una
/// hipótesis. Las palabras en las que coinciden dos hipótesis seguidas se dan
/// por estables y se escriben (LocalAgreement-2, como whisper_streaming). La
/// última palabra coincidente se retiene porque su puntuación todavía puede
/// cambiar. Al terminar el enunciado, la pasada final completa lo que falte.
///
/// Todo corre en main.
final class DictationSession {
    private let transcriber: Transcriber
    private let insert: (String) -> Void

    private(set) var text = ""               // todo lo escrito en esta sesión
    private var currentId = 0                // enunciado en curso
    private var committed: [String] = []     // palabras ya escritas del enunciado en curso
    private var previous: [String] = []      // hipótesis anterior del enunciado en curso
    private var contextBeforeUtterance = ""  // contexto para Whisper
    private var partialInFlight = false
    private var pendingFinals = 0

    var isIdle: Bool { pendingFinals == 0 }
    private static let debug = ProcessInfo.processInfo.environment["SPOKE_DEBUG"] != nil

    init(transcriber: Transcriber, insert: @escaping (String) -> Void) {
        self.transcriber = transcriber
        self.insert = insert
    }

    func partial(id: Int, samples: [Float]) {
        // Si Whisper sigue ocupado se saltea: la próxima pasada trae más audio.
        guard !partialInFlight, id == currentId else { return }
        partialInFlight = true
        transcriber.transcribe(samples, prompt: prompt, partial: true) { [weak self] hypothesis in
            guard let self else { return }
            self.partialInFlight = false
            guard id == self.currentId else { return }
            let words = Self.trimRepetition(Self.words(hypothesis))
            if Self.debug { print(String(format: "   parcial %.1fs: %@", Double(samples.count) / Config.sampleRate, hypothesis)) }
            var agreed = 0
            while agreed < min(self.previous.count, words.count),
                  Self.normalize(self.previous[agreed]) == Self.normalize(words[agreed]) {
                agreed += 1
            }
            let stable = agreed - 1
            if stable > self.committed.count,
               Self.matches(self.committed, words) {
                self.write(Array(words[self.committed.count..<stable]))
                self.committed = Array(words[..<stable])
            }
            self.previous = words
        }
    }

    func utterance(id: Int, samples: [Float], done: @escaping () -> Void) {
        pendingFinals += 1
        let finish = { [weak self] (hypothesis: String) in
            guard let self else { return }
            self.pendingFinals -= 1
            let words = Self.words(hypothesis)
            let start = self.resumeIndex(in: words)
            if start < words.count { self.write(Array(words[start...])) }
            self.currentId = id + 1
            self.committed = []
            self.previous = []
            self.contextBeforeUtterance = self.text
            done()
        }
        if samples.isEmpty {
            DispatchQueue.main.async { finish("") }
        } else {
            transcriber.transcribe(samples, prompt: prompt, completion: finish)
        }
    }

    private var prompt: String? {
        contextBeforeUtterance.isEmpty ? nil : String(contextBeforeUtterance.suffix(200))
    }

    private func write(_ words: [String]) {
        guard !words.isEmpty else { return }
        var piece = words.joined(separator: " ")
        if !text.isEmpty { piece = " " + piece }
        insert(piece)
        text += piece
    }

    /// Dónde retomar en la hipótesis final. La pasada final puede diferir de
    /// las parciales antes de ese punto (palabras agregadas, quitadas o
    /// unidas), así que se busca en toda la hipótesis dónde terminan las
    /// últimas palabras ya escritas: gana la coincidencia más larga y, a
    /// igualdad, la más cercana a `committed.count`.
    private func resumeIndex(in words: [String]) -> Int {
        guard !committed.isEmpty else { return 0 }
        let tail = committed.suffix(4).map(Self.normalize)
        let final = words.map(Self.normalize)
        let n = committed.count
        var best = (length: 0, index: n)
        for k in stride(from: 1, through: final.count, by: 1) {
            var length = 0
            while length < tail.count, k - 1 - length >= 0,
                  final[k - 1 - length] == tail[tail.count - 1 - length] {
                length += 1
            }
            if length > best.length || (length == best.length && length > 0 && abs(k - n) < abs(best.index - n)) {
                best = (length, k)
            }
        }
        return best.index
    }

    /// Lo ya escrito sigue siendo prefijo de la nueva hipótesis.
    private static func matches(_ committed: [String], _ words: [String]) -> Bool {
        guard committed.count <= words.count else { return false }
        return zip(committed, words).allSatisfy { normalize($0) == normalize($1) }
    }

    /// Las pasadas parciales a veces repiten ("x x x", o la frase entera dos
    /// veces). Corta la hipótesis donde empieza la repetición.
    private static func trimRepetition(_ words: [String]) -> [String] {
        let n = words.map(normalize)
        for i in 0..<n.count {
            if i + 2 < n.count, n[i] == n[i + 1], n[i] == n[i + 2] { return Array(words[..<i]) }
            let k = 3
            if i > 0, i + k <= n.count, n.count >= k, Array(n[i..<i + k]) == Array(n[0..<k]) {
                return Array(words[..<i])
            }
        }
        return words
    }

    private static func words(_ text: String) -> [String] {
        text.split(whereSeparator: \.isWhitespace).map(String.init)
    }

    private static func normalize(_ word: String) -> String {
        word.lowercased().trimmingCharacters(in: .punctuationCharacters.union(.symbols))
    }
}

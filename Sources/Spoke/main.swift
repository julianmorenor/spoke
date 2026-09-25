import AppKit
import SwiftUI

// Modo prueba sin micrófono ni UI: reproduce el archivo en tiempo real y
// muestra cuándo se escribiría cada trozo de texto.
//   Spoke --test audio.wav
if CommandLine.arguments.count == 3, CommandLine.arguments[1] == "--test" {
    runFileTest(path: CommandLine.arguments[2])
}

// Render del HUD a PNG para revisar el diseño:  Spoke --hud-snapshot out.png
if CommandLine.arguments.count == 3, CommandLine.arguments[1] == "--hud-snapshot" {
    MainActor.assumeIsolated { snapshotHUD(path: CommandLine.arguments[2]) }
    exit(0)
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory) // sin ícono en el Dock, solo barra de menú
app.run()

func runFileTest(path: String) -> Never {
    let transcriber = Transcriber()
    let capture = AudioCapture()
    var start = Date()
    var fed = false
    func t() -> String { String(format: "%5.2fs", Date().timeIntervalSince(start)) }

    let session = DictationSession(transcriber: transcriber) { piece in
        print("\(t()) escribe: \(piece.debugDescription)")
    }
    func finishIfDone() {
        guard fed, session.isIdle else { return }
        print("\(t()) texto final: \(session.text)")
        transcriber.shutdown()
        exit(0)
    }

    transcriber.load { ok in
        guard ok else { print("No se pudo cargar el modelo"); exit(1) }
        capture.onPartial = { id, samples in
            DispatchQueue.main.async { session.partial(id: id, samples: samples) }
        }
        capture.onUtterance = { id, samples in
            DispatchQueue.main.async {
                print("\(t()) fin de enunciado \(id)")
                session.utterance(id: id, samples: samples) { finishIfDone() }
            }
        }
        DispatchQueue.main.async {
            start = Date()
            print(" 0.00s empieza el audio")
            try? capture.feed(file: URL(fileURLWithPath: path)) {
                print("\(t()) termina el audio")
                fed = true
                finishIfDone()
            }
        }
    }
    dispatchMain()
}

@MainActor
func snapshotHUD(path: String) {
    let state = HUDState()
    state.levels = (0..<HUD.barCount).map { i in Float(0.15 + 0.85 * abs(sin(Double(i) * 0.7))) }
    let renderer = ImageRenderer(content: HUDView(state: state).padding(20).background(Color(white: 0.93)))
    renderer.scale = 3
    guard let image = renderer.cgImage else { return }
    let rep = NSBitmapImageRep(cgImage: image)
    try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: path))
    print(path)
}

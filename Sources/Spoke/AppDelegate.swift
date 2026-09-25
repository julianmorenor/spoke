import AppKit
import AVFoundation

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let transcriber = Transcriber()
    private let capture = AudioCapture()
    private let hud = HUD()
    private var hotKey: HotKey?
    private var statusItem: NSStatusItem!
    private var toggleItem: NSMenuItem!

    private var modelReady = false
    private var listening = false
    private var finishing = false
    private var session: DictationSession?

    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMenu()
        setStatus("Cargando modelo…")

        transcriber.load { ok in
            DispatchQueue.main.async {
                self.modelReady = ok
                self.setStatus(ok ? "Listo · \(Config.hotKeyLabel)" : "No se encontró el modelo en \(Config.modelPath)")
            }
        }

        capture.onLevel = { [weak self] level in self?.hud.state.push(level: level) }
        capture.onPartial = { [weak self] id, samples in
            DispatchQueue.main.async { self?.session?.partial(id: id, samples: samples) }
        }
        capture.onUtterance = { [weak self] id, samples in
            DispatchQueue.main.async {
                self?.session?.utterance(id: id, samples: samples) { self?.finishIfDone() }
            }
        }

        hotKey = HotKey(keyCode: Config.hotKeyCode, modifiers: Config.hotKeyModifiers) { [weak self] in
            DispatchQueue.main.async { self?.toggle() }
        }

        AVCaptureDevice.requestAccess(for: .audio) { _ in }
        if !TextInserter.isTrusted { TextInserter.requestPermission() }
    }

    func applicationWillTerminate(_ notification: Notification) {
        transcriber.shutdown()
    }

    // MARK: - Sesión de dictado

    @objc private func toggle() {
        if listening { stop() } else { start() }
    }

    private func start() {
        guard modelReady, !finishing else { NSSound.beep(); return }
        guard TextInserter.isTrusted else {
            TextInserter.requestPermission()
            return
        }
        do {
            try capture.start()
        } catch {
            setStatus("Error de micrófono: \(error.localizedDescription)")
            return
        }
        listening = true
        session = DictationSession(transcriber: transcriber) { TextInserter.type($0) }
        hud.show()
        updateIcon()
    }

    private func stop() {
        listening = false
        finishing = true
        hud.state.phase = .finishing
        capture.stop { [weak self] in
            self?.finishIfDone()
        }
        updateIcon()
    }

    private func finishIfDone() {
        guard finishing, session?.isIdle ?? true else { return }
        finishing = false
        hud.hide()
        updateIcon()
    }

    // MARK: - Barra de menú

    private func setupMenu() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        let menu = NSMenu()
        toggleItem = NSMenuItem(title: "Dictar (\(Config.hotKeyLabel))", action: #selector(toggle), keyEquivalent: "")
        toggleItem.target = self
        menu.addItem(toggleItem)
        menu.addItem(.separator())
        let status = NSMenuItem(title: "", action: nil, keyEquivalent: "")
        status.tag = 1
        menu.addItem(status)
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Salir", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        statusItem.menu = menu
        updateIcon()
    }

    private func setStatus(_ text: String) {
        statusItem.menu?.item(withTag: 1)?.title = text
    }

    private lazy var menuBarIcon: NSImage? = {
        let image = NSImage(named: "MenuBarIcon")
        image?.size = NSSize(width: 16, height: 16)
        image?.isTemplate = true // macOS lo adapta a modo claro/oscuro
        return image
    }()

    private func updateIcon() {
        statusItem.button?.image = menuBarIcon ?? NSImage(systemSymbolName: "waveform", accessibilityDescription: "Spoke")
        statusItem.button?.contentTintColor = listening ? .systemRed : (finishing ? .systemOrange : nil)
        toggleItem?.title = listening ? "Detener (\(Config.hotKeyLabel))" : "Dictar (\(Config.hotKeyLabel))"
    }
}

import AppKit
import SwiftUI

enum DictationPhase { case listening, finishing }

final class HUDState: ObservableObject {
    @Published var phase: DictationPhase = .listening
    @Published var levels: [Float] = Array(repeating: 0, count: HUD.barCount)

    func push(level: Float) {
        levels.removeFirst()
        levels.append(level)
    }
}

/// Píldora flotante abajo al centro con la onda de tu voz. Nunca toma el
/// foco, así el texto sigue yendo a la app en la que estás escribiendo.
final class HUD {
    static let barCount = 18
    static let size = NSSize(width: 150, height: 40)

    let state = HUDState()
    private lazy var panel: NSPanel = {
        let panel = NSPanel(contentRect: NSRect(origin: .zero, size: Self.size),
                            styleMask: [.nonactivatingPanel, .borderless],
                            backing: .buffered, defer: false)
        panel.isFloatingPanel = true
        panel.level = .statusBar
        panel.backgroundColor = .clear
        panel.isOpaque = false
        panel.hasShadow = false
        panel.ignoresMouseEvents = true
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        panel.contentView = NSHostingView(rootView: HUDView(state: state))
        return panel
    }()

    func show() {
        state.phase = .listening
        state.levels = Array(repeating: 0, count: Self.barCount)
        let screen = NSScreen.screens.first { NSMouseInRect(NSEvent.mouseLocation, $0.frame, false) } ?? NSScreen.main
        if let visible = screen?.visibleFrame {
            panel.setFrameOrigin(NSPoint(x: visible.midX - Self.size.width / 2, y: visible.minY + 28))
        }
        panel.alphaValue = 0
        panel.orderFrontRegardless()
        NSAnimationContext.runAnimationGroup { $0.duration = 0.15; panel.animator().alphaValue = 1 }
    }

    func hide() {
        NSAnimationContext.runAnimationGroup({ $0.duration = 0.2; panel.animator().alphaValue = 0 },
                                             completionHandler: { self.panel.orderOut(nil) })
    }
}

struct HUDView: View {
    @ObservedObject var state: HUDState

    // Los mismos colores del ícono (tools/make_icon.py).
    private static let orange = Color(red: 255 / 255, green: 146 / 255, blue: 84 / 255)
    private static let coral = Color(red: 255 / 255, green: 84 / 255, blue: 122 / 255)

    var body: some View {
        let listening = state.phase == .listening
        HStack(alignment: .center, spacing: 3) {
            ForEach(Array(state.levels.enumerated()), id: \.offset) { _, level in
                Capsule()
                    .fill(Color.white.opacity(listening ? 0.95 : 0.5))
                    .frame(width: 3, height: listening ? 4 + CGFloat(level) * 22 : 4)
            }
        }
        .animation(.easeOut(duration: 0.08), value: state.levels)
        .animation(.easeInOut(duration: 0.2), value: state.phase)
        .frame(width: HUD.size.width, height: HUD.size.height)
        .background(Capsule().fill(LinearGradient(colors: [Self.orange, Self.coral],
                                                  startPoint: .leading, endPoint: .trailing)))
        .overlay(Capsule().stroke(Color.white.opacity(0.25), lineWidth: 1))
    }
}

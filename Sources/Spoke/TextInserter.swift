import AppKit
import ApplicationServices

/// Escribe texto en la app que tenga el foco, simulando tecleo Unicode.
/// No toca el portapapeles. Requiere permiso de Accesibilidad.
enum TextInserter {
    static var isTrusted: Bool { AXIsProcessTrusted() }

    static func requestPermission() {
        let key = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
        AXIsProcessTrustedWithOptions([key: true] as CFDictionary)
    }

    static func type(_ text: String) {
        let source = CGEventSource(stateID: .combinedSessionState)
        let units = Array(text.utf16)
        // CGEvent acepta ~20 unidades UTF-16 por evento; mandamos en trozos.
        var i = 0
        while i < units.count {
            var end = min(i + 16, units.count)
            // No partir un par sustituto (emojis, etc.)
            if end < units.count, UTF16.isLeadSurrogate(units[end - 1]) { end -= 1 }
            var chunk = Array(units[i..<end])
            for keyDown in [true, false] {
                guard let event = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: keyDown) else { continue }
                event.flags = []
                event.keyboardSetUnicodeString(stringLength: chunk.count, unicodeString: &chunk)
                event.post(tap: .cghidEventTap)
            }
            i = end
        }
    }
}

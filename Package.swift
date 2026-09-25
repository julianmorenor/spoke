// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "Spoke",
    platforms: [.macOS(.v14)],
    targets: [
        // whisper.cpp instalado con Homebrew (brew install whisper-cpp)
        .systemLibrary(name: "CWhisper", path: "Sources/CWhisper"),
        .executableTarget(
            name: "Spoke",
            dependencies: ["CWhisper"],
            linkerSettings: [
                .unsafeFlags(["-L/opt/homebrew/lib", "-Xlinker", "-rpath", "-Xlinker", "/opt/homebrew/lib"]),
            ]
        ),
    ]
)

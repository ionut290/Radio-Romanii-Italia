import SwiftUI
import AVFoundation

@MainActor
final class RadioPlayer: ObservableObject {
    @Published var isPlaying = false
    @Published var errorMessage: String?
    private var player: AVPlayer?
    private let streamURL = URL(string: "https://radio-romanii-italia.duckdns.org/listen/radio-romanii-italia/radio.mp3")!

    func toggle() {
        if isPlaying {
            player?.pause()
            isPlaying = false
            return
        }
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default)
            try AVAudioSession.sharedInstance().setActive(true)
            if player == nil { player = AVPlayer(url: streamURL) }
            player?.play()
            isPlaying = true
            errorMessage = nil
        } catch {
            errorMessage = "Impossibile avviare l'audio: \(error.localizedDescription)"
            isPlaying = false
        }
    }
}

@main
struct RadioRomaniiItaliaApp: App {
    @StateObject private var radio = RadioPlayer()

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                VStack(spacing: 24) {
                    Image(systemName: "antenna.radiowaves.left.and.right")
                        .font(.system(size: 74))
                        .foregroundStyle(.orange)
                        .accessibilityHidden(true)
                    Text("Radio Românii din Italia")
                        .font(.largeTitle.bold())
                        .multilineTextAlignment(.center)
                    Text("Muzică, știri și comunitate")
                        .foregroundStyle(.secondary)
                    Button(action: { radio.toggle() }) {
                        Label(radio.isPlaying ? "Oprește radio" : "Ascultă live",
                              systemImage: radio.isPlaying ? "stop.fill" : "play.fill")
                            .font(.title2.bold())
                            .frame(maxWidth: .infinity)
                            .padding()
                    }
                    .buttonStyle(.borderedProminent)
                    .accessibilityHint("Controlla la riproduzione audio della radio")
                    if let error = radio.errorMessage {
                        Text(error).foregroundStyle(.red)
                    }
                    Link("Notizie e comunità", destination: URL(string: "https://radioromanii.duckdns.org/")!)
                        .font(.headline)
                    Spacer()
                }
                .padding(24)
                .navigationTitle("RDI")
            }
        }
    }
}

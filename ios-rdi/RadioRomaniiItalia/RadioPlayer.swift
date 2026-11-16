import AVFoundation
import MediaPlayer
import SwiftUI

/// Player nativo unico: una sola sorgente sonora alla volta (live o AI MUSIC).
@MainActor
final class RadioPlayer: ObservableObject {
    @Published private(set) var isPlaying = false
    @Published private(set) var isBuffering = false
    @Published private(set) var isLive = true
    @Published private(set) var currentTrackID: String?
    @Published private(set) var currentTitle = "Radio Românii din Italia"
    @Published private(set) var currentArtist = "Muzică, știri și comunitate"
    @Published var errorMessage: String?

    private let streamURL = URL(string: "https://radio-romanii-italia.duckdns.org/listen/radio-romanii-italia/radio.mp3")!
    private let musicBaseURL = "https://radio-romanii-italia.duckdns.org/api/ai-music/spotlight"
    private var activeURL: URL
    private var player: AVPlayer?
    private var playbackObservation: NSKeyValueObservation?
    private var interruptionObserver: NSObjectProtocol?
    private var remoteTargets: [Any] = []

    init() {
        activeURL = streamURL
        configureRemoteCommands()
        interruptionObserver = NotificationCenter.default.addObserver(
            forName: AVAudioSession.interruptionNotification,
            object: AVAudioSession.sharedInstance(),
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor [weak self] in
                self?.handleInterruption(notification)
            }
        }
    }

    /// Riprende la sorgente attualmente selezionata.
    func toggle() {
        isPlaying ? pause() : play()
    }

    /// Torna alla radio normale, evitando doppie riproduzioni.
    func playLive() {
        if !isLive {
            selectSource(streamURL, title: "Radio Românii din Italia",
                         artist: "Muzică, știri și comunitate", trackID: nil)
        }
        play()
    }

    /// Solo registrazioni già autorizzate e pubblicate dal backend RDI.
    func toggleAITrack(id: String, title: String, artist: String) {
        guard id.range(of: "^[0-9a-f]{32}$", options: .regularExpression) != nil else {
            errorMessage = "Piesa selectată nu este disponibilă."
            return
        }
        if currentTrackID == id && !isLive {
            toggle()
            return
        }
        guard let url = URL(string: "\(musicBaseURL)/\(id)/audio") else {
            errorMessage = "Adresa piesei nu este validă."
            return
        }
        selectSource(url, title: title, artist: artist, trackID: id)
        play()
    }

    private func selectSource(_ url: URL, title: String, artist: String, trackID: String?) {
        player?.pause()
        activeURL = url
        isLive = trackID == nil
        currentTrackID = trackID
        currentTitle = title
        currentArtist = artist
        isPlaying = false
        isBuffering = false
        errorMessage = nil
        if let player {
            player.replaceCurrentItem(with: AVPlayerItem(url: url))
        }
        updateNowPlaying()
    }

    func play() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default)
            try session.setActive(true)

            if player == nil {
                let newPlayer = AVPlayer(url: activeURL)
                newPlayer.automaticallyWaitsToMinimizeStalling = true
                player = newPlayer
                playbackObservation = newPlayer.observe(
                    \.timeControlStatus, options: [.initial, .new]
                ) { [weak self] observedPlayer, _ in
                    let waiting = observedPlayer.timeControlStatus == .waitingToPlayAtSpecifiedRate
                    Task { @MainActor [weak self] in
                        self?.isBuffering = (self?.isPlaying == true) && waiting
                    }
                }
            }

            player?.play()
            isPlaying = true
            isBuffering = true
            errorMessage = nil
            updateNowPlaying()
        } catch {
            isPlaying = false
            isBuffering = false
            errorMessage = "Nu se poate porni audio: \(error.localizedDescription)"
        }
    }

    func pause() {
        player?.pause()
        isPlaying = false
        isBuffering = false
        updateNowPlaying()
        try? AVAudioSession.sharedInstance().setActive(
            false, options: [.notifyOthersOnDeactivation]
        )
    }

    private func updateNowPlaying() {
        MPNowPlayingInfoCenter.default().nowPlayingInfo = [
            MPMediaItemPropertyTitle: currentTitle,
            MPMediaItemPropertyArtist: currentArtist,
            MPNowPlayingInfoPropertyIsLiveStream: isLive,
            MPNowPlayingInfoPropertyPlaybackRate: isPlaying ? 1.0 : 0.0
        ]
    }

    private func configureRemoteCommands() {
        let commands = MPRemoteCommandCenter.shared()
        commands.playCommand.isEnabled = true
        commands.pauseCommand.isEnabled = true
        commands.togglePlayPauseCommand.isEnabled = true

        remoteTargets.append(commands.playCommand.addTarget { [weak self] _ in
            Task { @MainActor [weak self] in self?.play() }
            return .success
        })
        remoteTargets.append(commands.pauseCommand.addTarget { [weak self] _ in
            Task { @MainActor [weak self] in self?.pause() }
            return .success
        })
        remoteTargets.append(commands.togglePlayPauseCommand.addTarget { [weak self] _ in
            Task { @MainActor [weak self] in self?.toggle() }
            return .success
        })
    }

    private func handleInterruption(_ notification: Notification) {
        guard let rawType = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: rawType) else { return }
        switch type {
        case .began:
            isPlaying = false
            isBuffering = false
            updateNowPlaying()
        case .ended:
            let rawOptions = notification.userInfo?[AVAudioSessionInterruptionOptionKey] as? UInt ?? 0
            if AVAudioSession.InterruptionOptions(rawValue: rawOptions).contains(.shouldResume) {
                play()
            }
        @unknown default: break
        }
    }
}

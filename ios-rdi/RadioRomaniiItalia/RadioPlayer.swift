import AVFoundation
import MediaPlayer
import SwiftUI

/// Player nativ, păstrat la nivelul aplicației: continuă când ecranul se blochează.
@MainActor
final class RadioPlayer: ObservableObject {
    @Published private(set) var isPlaying = false
    @Published private(set) var isBuffering = false
    @Published var errorMessage: String?

    private let streamURL = URL(string: "https://radio-romanii-italia.duckdns.org/listen/radio-romanii-italia/radio.mp3")!
    private var player: AVPlayer?
    private var playbackObservation: NSKeyValueObservation?
    private var interruptionObserver: NSObjectProtocol?
    private var remoteTargets: [Any] = []

    init() {
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

    func toggle() {
        isPlaying ? pause() : play()
    }

    func play() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default)
            try session.setActive(true)

            if player == nil {
                let newPlayer = AVPlayer(url: streamURL)
                newPlayer.automaticallyWaitsToMinimizeStalling = true
                player = newPlayer
                playbackObservation = newPlayer.observe(
                    \.timeControlStatus, options: [.initial, .new]
                ) { [weak self] player, _ in
                    let waiting = player.timeControlStatus == .waitingToPlayAtSpecifiedRate
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
            errorMessage = "Nu se poate porni radioul: \(error.localizedDescription)"
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
            MPMediaItemPropertyTitle: "Radio Românii din Italia",
            MPMediaItemPropertyArtist: "Muzică, știri și comunitate",
            MPNowPlayingInfoPropertyIsLiveStream: true,
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
              let type = AVAudioSession.InterruptionType(rawValue: rawType) else {
            return
        }

        switch type {
        case .began:
            // iOS întrerupe sunetul în timpul apelurilor.
            isPlaying = false
            isBuffering = false
            updateNowPlaying()
        case .ended:
            let rawOptions = notification.userInfo?[AVAudioSessionInterruptionOptionKey] as? UInt ?? 0
            let options = AVAudioSession.InterruptionOptions(rawValue: rawOptions)
            if options.contains(.shouldResume) {
                play()
            }
        @unknown default:
            break
        }
    }
}

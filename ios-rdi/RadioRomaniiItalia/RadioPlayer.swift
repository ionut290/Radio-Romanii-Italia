import AVFoundation
import MediaPlayer
import SwiftUI
import UIKit

/// Un unico AVPlayer per la diretta RDI e i brani AI: mai due audio sovrapposti.
@MainActor
final class RadioPlayer: ObservableObject {
    @Published private(set) var isPlaying = false
    @Published private(set) var isBuffering = false
    @Published private(set) var currentAITrack: RDIAITrack?
    @Published var errorMessage: String?

    private let liveURL = URL(
        string: "https://radio-romanii-italia.duckdns.org/listen/radio-romanii-italia/radio.mp3"
    )!

    private var activeURL: URL
    private var player: AVPlayer?
    private var timeControlObservation: NSKeyValueObservation?
    private var itemStatusObservation: NSKeyValueObservation?
    private var interruptionObserver: NSObjectProtocol?
    private var foregroundObserver: NSObjectProtocol?
    private var endedObserver: NSObjectProtocol?
    private var stalledObserver: NSObjectProtocol?
    private var failedObserver: NSObjectProtocol?
    private var remoteTargets: [Any] = []
    private var aiQueue: [RDIAITrack] = []
    private var currentAIIndex: Int?
    private var retryTask: Task<Void, Never>?
    private var retryCount = 0
    private var consecutiveAIFailures = 0
    private var playbackGeneration = 0
    private var shouldResumeAfterInterruption = false

    var isRadioPlaying: Bool { currentAITrack == nil && isPlaying }
    var canSkipAI: Bool { currentAITrack != nil && aiQueue.count > 1 }

    init() {
        activeURL = liveURL
        configureRemoteCommands()

        interruptionObserver = NotificationCenter.default.addObserver(
            forName: AVAudioSession.interruptionNotification,
            object: AVAudioSession.sharedInstance(),
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor [weak self] in self?.handleInterruption(notification) }
        }

        foregroundObserver = NotificationCenter.default.addObserver(
            forName: UIApplication.didBecomeActiveNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in self?.resumeIfNeeded() }
        }

        endedObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor [weak self] in
                guard let self,
                      let item = notification.object as? AVPlayerItem,
                      item === self.player?.currentItem else { return }
                if self.currentAITrack != nil {
                    self.nextAITrack()
                }
            }
        }

        stalledObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemPlaybackStalled,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor [weak self] in
                guard let self, self.isPlaying,
                      let item = notification.object as? AVPlayerItem,
                      item === self.player?.currentItem else { return }
                self.isBuffering = true
                self.player?.play()
                self.scheduleReconnect()
            }
        }

        failedObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemFailedToPlayToEndTime,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            Task { @MainActor [weak self] in
                guard let self, let item = notification.object as? AVPlayerItem,
                      item === self.player?.currentItem else { return }
                guard self.isPlaying else { return }
                self.isBuffering = true
                self.scheduleReconnect()
            }
        }
    }

    /// Mantiene il vecchio comando per la radio; in AI Music il toggle riguarda il brano.
    func toggle() {
        isPlaying ? pause() : play()
    }

    /// Il tasto principale Radio avvia sempre la diretta, anche se era attiva AI Music.
    func toggleLive() {
        if currentAITrack != nil {
            playLive()
        } else {
            toggle()
        }
    }

    func playLive() {
        if currentAITrack != nil {
            currentAITrack = nil
            aiQueue = []
            currentAIIndex = nil
            replaceSource(with: liveURL)
        }
        play()
    }

    /// Riproduci il brano scelto nella playlist approvata dall'API RDI.
    func playAITrack(_ track: RDIAITrack, queue: [RDIAITrack]) {
        guard queue.contains(track),
              let url = track.audioURL else {
            errorMessage = "Questo brano non è disponibile."
            return
        }
        aiQueue = queue.filter { $0.audioURL != nil }
        guard let validIndex = aiQueue.firstIndex(of: track) else { return }
        if currentAITrack?.id == track.id {
            toggle()
            return
        }
        currentAIIndex = validIndex
        consecutiveAIFailures = 0
        currentAITrack = track
        replaceSource(with: url)
        play()
    }

    func nextAITrack() {
        skipAITrack(forward: true)
    }

    func previousAITrack() {
        skipAITrack(forward: false)
    }

    private func skipAITrack(forward: Bool) {
        guard currentAITrack != nil, !aiQueue.isEmpty,
              let position = currentAIIndex else { return }
        let nextIndex = (position + (forward ? 1 : -1) + aiQueue.count) % aiQueue.count
        let next = aiQueue[nextIndex]
        guard let url = next.audioURL else { return }
        currentAIIndex = nextIndex
        currentAITrack = next
        replaceSource(with: url)
        play()
    }

    private func replaceSource(with url: URL) {
        retryTask?.cancel()
        retryTask = nil
        retryCount = 0
        playbackGeneration += 1
        player?.pause()
        activeURL = url
        isPlaying = false
        isBuffering = false
        errorMessage = nil
        if let player {
            let item = makeItem(for: url)
            itemStatusObservation?.invalidate()
            itemStatusObservation = nil
            player.replaceCurrentItem(with: item)
            observeAudioItem(item)
        }
        updateRemoteCommands()
        updateNowPlaying()
    }

    private func makeItem(for url: URL) -> AVPlayerItem {
        let item = AVPlayerItem(url: url)
        // A modest forward buffer reduces gaps on mobile networks.
        item.preferredForwardBufferDuration = currentAITrack == nil ? 3 : 8
        return item
    }

    private func observeAudioItem(_ item: AVPlayerItem) {
        itemStatusObservation?.invalidate()
        itemStatusObservation = item.observe(\.status, options: [.new]) { [weak self] observedItem, _ in
            guard observedItem.status == .failed else { return }
            Task { @MainActor [weak self] in
                guard let self, self.player?.currentItem === observedItem,
                      self.isPlaying else { return }
                self.isBuffering = true
                self.scheduleReconnect()
            }
        }
    }

    func play() {
        if !isPlaying { retryCount = 0 }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default)
            try session.setActive(true)

            if player == nil {
                let newPlayer = AVPlayer(playerItem: makeItem(for: activeURL))
                newPlayer.automaticallyWaitsToMinimizeStalling = true
                player = newPlayer
                if let item = newPlayer.currentItem { observeAudioItem(item) }
                timeControlObservation = newPlayer.observe(
                    \.timeControlStatus, options: [.initial, .new]
                ) { [weak self] observedPlayer, _ in
                    let waiting = observedPlayer.timeControlStatus == .waitingToPlayAtSpecifiedRate
                    Task { @MainActor [weak self] in
                        guard let self, self.player === observedPlayer else { return }
                        self.isBuffering = self.isPlaying && waiting
                        if observedPlayer.timeControlStatus == .playing {
                            self.retryTask?.cancel()
                            self.retryTask = nil
                            self.retryCount = 0
                            self.consecutiveAIFailures = 0
                            self.errorMessage = nil
                        } else if self.isPlaying && waiting {
                            self.scheduleReconnect()
                        }
                    }
                }
            } else if player?.currentItem?.status == .failed {
                let item = makeItem(for: activeURL)
                player?.replaceCurrentItem(with: item)
                observeAudioItem(item)
            }

            player?.play()
            isPlaying = true
            isBuffering = player?.timeControlStatus != .playing
            errorMessage = nil
            updateNowPlaying()
            if isBuffering {
                scheduleReconnect()
            }
        } catch {
            isPlaying = false
            isBuffering = false
            errorMessage = "Impossibile riprodurre l'audio: \(error.localizedDescription)"
        }
    }

    func pause() {
        retryTask?.cancel()
        retryTask = nil
        playbackGeneration += 1
        player?.pause()
        isPlaying = false
        isBuffering = false
        shouldResumeAfterInterruption = false
        updateNowPlaying()
        try? AVAudioSession.sharedInstance().setActive(
            false, options: [.notifyOthersOnDeactivation]
        )
    }

    private func resumeIfNeeded() {
        // Non riavviare una riproduzione messa volontariamente in pausa.
        guard isPlaying, player?.rate == 0 else { return }
        if player?.currentItem?.status == .failed {
            let item = makeItem(for: activeURL)
            player?.replaceCurrentItem(with: item)
            observeAudioItem(item)
        }
        do { try AVAudioSession.sharedInstance().setActive(true) }
        catch { return }
        player?.play()
        scheduleReconnect()
    }

    /// Recovery for BOTH live and AI audio. Stops on manual pause or source switch.
    private func scheduleReconnect() {
        guard isPlaying, retryTask == nil,
              player?.timeControlStatus != .playing else { return }
        let isLive = currentAITrack == nil
        let maxAttempts = isLive ? 6 : 3
        guard retryCount < maxAttempts else {
            retryTask = nil
            retryCount = 0
            if !isLive && !aiQueue.isEmpty {
                consecutiveAIFailures += 1
                if consecutiveAIFailures < min(aiQueue.count, 4) && aiQueue.count > 1 {
                    skipAITrack(forward: true)
                    return
                }
            }
            player?.pause()
            isPlaying = false
            isBuffering = false
            errorMessage = isLive
                ? "Connessione radio non disponibile. Tocca Play per riprovare."
                : "Brano non disponibile. Controlla la connessione o scegli un altro brano."
            updateNowPlaying()
            return
        }
        let delays = isLive ? [5, 3, 5, 8, 13, 20] : [4, 6, 10]
        let delay = delays[retryCount]
        let generation = playbackGeneration
        retryTask = Task { [weak self] in
            do {
                try await Task.sleep(nanoseconds: UInt64(delay) * 1_000_000_000)
            } catch {
                return
            }
            guard let self, !Task.isCancelled, self.isPlaying,
                  self.playbackGeneration == generation else { return }
            self.retryTask = nil
            guard self.player?.timeControlStatus != .playing else {
                self.retryCount = 0
                return
            }
            self.retryCount += 1
            self.isBuffering = true
            self.errorMessage = self.currentAITrack == nil
                ? "Riconnessione radio in corso…"
                : "Riconnessione AI Music in corso…"
            let item = self.makeItem(for: self.activeURL)
            self.player?.replaceCurrentItem(with: item)
            self.observeAudioItem(item)
            self.player?.play()
            self.scheduleReconnect()
        }
    }

    private func updateNowPlaying() {
        let isLive = currentAITrack == nil
        MPNowPlayingInfoCenter.default().nowPlayingInfo = [
            MPMediaItemPropertyTitle: currentAITrack?.title ?? "Radio Românii din Italia",
            MPMediaItemPropertyArtist: currentAITrack?.artist ?? "Musica, notizie e comunità",
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

        remoteTargets.append(commands.nextTrackCommand.addTarget { [weak self] _ in
            Task { @MainActor [weak self] in self?.nextAITrack() }
            return .success
        })
        remoteTargets.append(commands.previousTrackCommand.addTarget { [weak self] _ in
            Task { @MainActor [weak self] in self?.previousAITrack() }
            return .success
        })

        updateRemoteCommands()
    }

    private func updateRemoteCommands() {
        let commands = MPRemoteCommandCenter.shared()
        commands.nextTrackCommand.isEnabled = canSkipAI
        commands.previousTrackCommand.isEnabled = canSkipAI
    }

    private func handleInterruption(_ notification: Notification) {
        guard let raw = notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: raw) else { return }
        switch type {
        case .began:
            shouldResumeAfterInterruption = isPlaying
            player?.pause()
            retryTask?.cancel()
            retryTask = nil
            isPlaying = false
            isBuffering = false
            updateNowPlaying()
        case .ended:
            let rawOptions = notification.userInfo?[AVAudioSessionInterruptionOptionKey] as? UInt ?? 0
            let allowed = AVAudioSession.InterruptionOptions(rawValue: rawOptions).contains(.shouldResume)
            let resume = shouldResumeAfterInterruption && allowed
            shouldResumeAfterInterruption = false
            if resume { play() }
        @unknown default:
            break
        }
    }
}

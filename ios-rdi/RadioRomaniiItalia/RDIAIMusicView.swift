import SwiftUI

private enum RDIAIMusicSection: String, CaseIterable {
    case ranking = "Top 3"
    case tracks = "Tutti i brani"
    case artists = "Artisti"
}

/// Schermata SwiftUI completamente nativa, senza webview per la musica AI.
/// I titoli e gli artisti provengono esclusivamente dalla playlist pubblica RDI.
struct RDIAIMusicView: View {
    @EnvironmentObject private var radio: RadioPlayer
    @ObservedObject var store: RDIAIMusicStore
    @State private var section: RDIAIMusicSection = .ranking

    private let magenta = Color(red: 0.97, green: 0.19, blue: 0.79)
    private let violet = Color(red: 0.62, green: 0.26, blue: 0.99)
    private let aqua = Color(red: 0.18, green: 0.75, blue: 1.0)

    var body: some View {
        VStack(alignment: .leading, spacing: 19) {
            title
            selectedTrackPlayer
            sections

            if store.isLoading && store.tracks.isEmpty {
                ProgressView("Caricamento dei brani AI…")
                    .tint(magenta)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 24)
            } else if store.tracks.isEmpty {
                emptyState
            } else {
                switch section {
                case .ranking:
                    rankingSection
                    trackSection(title: "Tutti i brani", limit: 12)
                case .tracks:
                    trackSection(title: "Brani disponibili", limit: nil)
                case .artists:
                    artistsSection
                }
            }
        }
        .task {
            if store.tracks.isEmpty { await store.refresh() }
        }
    }

    private var title: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(spacing: 10) {
                Image(systemName: "headphones")
                    .font(.system(size: 28, weight: .medium))
                    .foregroundStyle(magenta)
                    .shadow(color: magenta.opacity(0.8), radius: 9)

                Text("AI MUSIC")
                    .font(.system(size: 30, weight: .black, design: .rounded))
                    .italic()
                    .foregroundStyle(
                        LinearGradient(colors: [.white, magenta, aqua],
                                       startPoint: .leading, endPoint: .trailing)
                    )

                Spacer()
                Button {
                    Task { await store.refresh() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.headline)
                        .frame(width: 40, height: 40)
                        .foregroundStyle(.white)
                        .background(RDITheme.panel, in: Circle())
                }
                .accessibilityLabel("Aggiorna brani AI")
            }
            Text("Musica originale della comunità RDI")
                .font(.subheadline)
                .foregroundStyle(RDITheme.muted)
        }
    }

    private var selectedTrackPlayer: some View {
        VStack(spacing: 12) {
            HStack(spacing: 13) {
                artwork(for: radio.currentAITrack, size: 73)
                VStack(alignment: .leading, spacing: 5) {
                    Text(radio.currentAITrack?.title ?? "Scegli un brano")
                        .font(.system(size: 17, weight: .bold))
                        .foregroundStyle(.white)
                        .lineLimit(2)
                    Text(radio.currentAITrack?.artist ?? "RDI AI Music")
                        .font(.subheadline)
                        .foregroundStyle(RDITheme.muted)
                        .lineLimit(1)
                    if radio.isBuffering && radio.currentAITrack != nil {
                        Text("Caricamento audio…")
                            .font(.caption)
                            .foregroundStyle(aqua)
                    }
                }
                Spacer(minLength: 0)
                Image(systemName: "waveform")
                    .font(.title2)
                    .foregroundStyle(magenta)
            }
            RDIWaveform(isPlaying: radio.currentAITrack != nil && radio.isPlaying,
                        reduceMotion: !radio.isPlaying)
                .frame(height: 26)

            HStack(spacing: 28) {
                Button { radio.previousAITrack() } label: {
                    Image(systemName: "backward.end.fill")
                        .font(.system(size: 25))
                        .frame(width: 47, height: 50)
                }
                .disabled(!radio.canSkipAI)
                .accessibilityLabel("Brano precedente")

                Button {
                    if radio.currentAITrack != nil {
                        radio.toggle()
                    } else if let first = store.tracks.first {
                        radio.playAITrack(first, queue: store.tracks)
                    }
                } label: {
                    Image(systemName: radio.currentAITrack != nil && radio.isPlaying
                          ? "pause.fill" : "play.fill")
                        .font(.system(size: 24, weight: .bold))
                        .frame(width: 64, height: 64)
                        .background(
                            LinearGradient(colors: [magenta, violet, aqua],
                                           startPoint: .topLeading, endPoint: .bottomTrailing),
                            in: Circle()
                        )
                        .shadow(color: magenta.opacity(0.75), radius: 14)
                }
                .disabled(store.tracks.isEmpty && radio.currentAITrack == nil)
                .accessibilityLabel(radio.isPlaying && radio.currentAITrack != nil
                                    ? "Pausa AI Music" : "Riproduci AI Music")

                Button { radio.nextAITrack() } label: {
                    Image(systemName: "forward.end.fill")
                        .font(.system(size: 25))
                        .frame(width: 47, height: 50)
                }
                .disabled(!radio.canSkipAI)
                .accessibilityLabel("Brano successivo")
            }
            .foregroundStyle(.white)
            .buttonStyle(.plain)

            if radio.currentAITrack != nil {
                HStack(spacing: 7) {
                    Image(systemName: "music.note")
                    Text("Ascolto all'interno dell'app")
                    Spacer()
                    Text("RDI AI")
                }
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(RDITheme.muted)
            }

            if let error = radio.errorMessage {
                Label(error, systemImage: "exclamationmark.triangle")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
        }
        .padding(17)
        .frame(maxWidth: .infinity)
        .background(
            LinearGradient(
                colors: [Color(red: 0.17, green: 0.09, blue: 0.34),
                         Color(red: 0.06, green: 0.10, blue: 0.25)],
                startPoint: .topLeading, endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 23)
        )
        .overlay(RoundedRectangle(cornerRadius: 23)
            .stroke(LinearGradient(colors: [magenta, aqua, violet],
                                   startPoint: .topLeading, endPoint: .bottomTrailing),
                    lineWidth: 1.6))
        .shadow(color: magenta.opacity(0.31), radius: 13)
    }

    private var sections: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 9) {
                ForEach(RDIAIMusicSection.allCases, id: \.self) { item in
                    Button {
                        withAnimation(.easeInOut(duration: 0.18)) { section = item }
                    } label: {
                        HStack(spacing: 5) {
                            Image(systemName: item == .ranking ? "trophy.fill" :
                                  (item == .tracks ? "music.note.list" : "person.2.fill"))
                            Text(item.rawValue)
                        }
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 13)
                        .padding(.vertical, 10)
                        .background(section == item ? magenta : RDITheme.panel,
                                    in: Capsule())
                        .overlay(Capsule().stroke(section == item ? magenta : aqua.opacity(0.45)))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var rankingSection: some View {
        VStack(alignment: .leading, spacing: 11) {
            Label("Top 3 della community", systemImage: "trophy.fill")
                .font(.headline)
                .foregroundStyle(.white)
            Text("Brani approvati, ordinati secondo i voti pubblicati da RDI.")
                .font(.caption)
                .foregroundStyle(RDITheme.muted)

            ForEach(Array(store.tracks.prefix(3).enumerated()), id: \.element.id) { index, track in
                Button { radio.playAITrack(track, queue: store.tracks) } label: {
                    HStack(spacing: 12) {
                        Text("\(index + 1)")
                            .font(.title2.bold())
                            .foregroundStyle(index == 0 ? .yellow : aqua)
                            .frame(width: 27)
                        artwork(for: track, size: 54)
                        trackName(track)
                        Spacer(minLength: 0)
                        Image(systemName: radio.currentAITrack?.id == track.id && radio.isPlaying
                              ? "pause.circle.fill" : "play.circle.fill")
                            .font(.title)
                            .foregroundStyle(magenta)
                    }
                    .padding(11)
                    .background(RDITheme.panel, in: RoundedRectangle(cornerRadius: 16))
                    .overlay(RoundedRectangle(cornerRadius: 16)
                        .stroke(index == 0 ? Color.yellow.opacity(0.58) : violet.opacity(0.38)))
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func trackSection(title: String, limit: Int?) -> some View {
        let chosen = limit.map { Array(store.tracks.prefix($0)) } ?? store.tracks
        return VStack(alignment: .leading, spacing: 10) {
            Label(title, systemImage: "music.note.list")
                .font(.headline)
                .foregroundStyle(.white)
            LazyVStack(spacing: 8) {
                ForEach(chosen) { track in
                    Button { radio.playAITrack(track, queue: store.tracks) } label: {
                        HStack(spacing: 11) {
                            artwork(for: track, size: 49)
                            trackName(track)
                            Spacer()
                            Image(systemName: radio.currentAITrack?.id == track.id && radio.isPlaying
                                  ? "pause.fill" : "play.fill")
                                .font(.body.bold())
                                .foregroundStyle(magenta)
                                .frame(width: 34, height: 44)
                        }
                        .padding(.horizontal, 11)
                        .padding(.vertical, 8)
                        .background(RDITheme.panel.opacity(0.92),
                                    in: RoundedRectangle(cornerRadius: 14))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var artistsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Artisti RDI AI", systemImage: "person.2.fill")
                .font(.headline)
                .foregroundStyle(.white)

            let names = Array(Set(store.tracks.map(\.artist))).sorted {
                $0.localizedStandardCompare($1) == .orderedAscending
            }

            ForEach(names, id: \.self) { artist in
                VStack(alignment: .leading, spacing: 7) {
                    Label(artist, systemImage: "person.crop.circle")
                        .font(.headline)
                        .foregroundStyle(.white)
                    ForEach(store.tracks.filter { $0.artist == artist }) { track in
                        Button {
                            radio.playAITrack(track, queue: store.tracks)
                        } label: {
                            HStack {
                                Text(track.title)
                                    .font(.subheadline)
                                    .foregroundStyle(RDITheme.muted)
                                Spacer()
                                Image(systemName: "play.circle")
                                    .foregroundStyle(magenta)
                            }
                        }
                    }
                }
                .padding(14)
                .background(RDITheme.panel, in: RoundedRectangle(cornerRadius: 15))
            }
        }
    }

    private func trackName(_ track: RDIAITrack) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(track.title)
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(.white)
                .lineLimit(2)
            Text(track.artist)
                .font(.caption)
                .foregroundStyle(RDITheme.muted)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // L'API attuale non offre copertine: usa un'immagine grafica,
    // senza inventare fotografie o attribuirle agli artisti.
    private func artwork(for track: RDIAITrack?, size: CGFloat) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12)
                .fill(
                    LinearGradient(colors: [violet, RDITheme.background, magenta],
                                   startPoint: .topLeading, endPoint: .bottomTrailing)
                )
            Image(systemName: "music.note")
                .font(.system(size: size * 0.39, weight: .bold))
                .foregroundStyle(.white)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }

    private var emptyState: some View {
        VStack(spacing: 11) {
            Image(systemName: "music.note.list")
                .font(.largeTitle)
                .foregroundStyle(magenta)
            Text(store.errorMessage ?? "Non ci sono ancora brani disponibili.")
                .font(.subheadline)
                .foregroundStyle(RDITheme.muted)
                .multilineTextAlignment(.center)
            Button("Riprova") { Task { await store.refresh() } }
                .buttonStyle(.borderedProminent)
                .tint(violet)
        }
        .frame(maxWidth: .infinity)
        .padding(26)
        .background(RDITheme.panel, in: RoundedRectangle(cornerRadius: 18))
    }
}

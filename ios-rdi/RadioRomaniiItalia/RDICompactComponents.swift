import SwiftUI

/// Mini radio in alto: la home riserva la maggior parte dello spazio alle notizie.
struct RDICompactRadioPlayer: View {
    @ObservedObject var radio: RadioPlayer
    let reduceMotion: Bool

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 13)
                    .fill(RDITheme.orange.opacity(0.24))
                Image(systemName: "mic.fill")
                    .font(.system(size: 27))
                    .foregroundStyle(RDITheme.orange)
            }
            .frame(width: 51, height: 57)

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 5) {
                    Circle()
                        .fill(radio.isRadioPlaying ? Color.green : Color.orange)
                        .frame(width: 7, height: 7)
                    Text("RADIO LIVE")
                        .font(.system(size: 10, weight: .heavy))
                        .foregroundStyle(RDITheme.orange)
                }
                Text("Radio Românii din Italia")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .minimumScaleFactor(0.75)
                Text(radio.isRadioPlaying
                     ? (radio.isBuffering ? "Connessione…" : "In riproduzione")
                     : "Ascolta la diretta RDI")
                    .font(.system(size: 10))
                    .foregroundStyle(RDITheme.muted)
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
            Button(action: radio.toggleLive) {
                Image(systemName: radio.isRadioPlaying ? "pause.fill" : "play.fill")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(width: 47, height: 47)
                    .background(
                        LinearGradient(colors: [RDITheme.orange, .red, RDITheme.violet],
                                       startPoint: .topLeading, endPoint: .bottomTrailing),
                        in: Circle()
                    )
            }
            .buttonStyle(.plain)
            .accessibilityLabel(radio.isRadioPlaying ? "Pausa radio" : "Riproduci la radio")
        }
        .padding(13)
        .frame(maxWidth: .infinity)
        .background(
            LinearGradient(colors: [RDITheme.panel, Color(red: 0.09, green: 0.08, blue: 0.24)],
                           startPoint: .leading, endPoint: .trailing),
            in: RoundedRectangle(cornerRadius: 19)
        )
        .overlay(RoundedRectangle(cornerRadius: 19)
            .stroke(RDITheme.violet.opacity(0.65), lineWidth: 1))
    }
}

struct RDICompactTile: View {
    let title: String
    let subtitle: String
    let symbol: String
    let colors: [Color]
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: symbol)
                    .font(.system(size: 16, weight: .bold))
                Text(title)
                    .font(.system(size: 10, weight: .heavy))
                    .lineLimit(2)
                    .minimumScaleFactor(0.7)
                    .multilineTextAlignment(.leading)
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .frame(height: 55)
            .padding(.horizontal, 5)
            .background(
                LinearGradient(colors: colors, startPoint: .topLeading,
                               endPoint: .bottomTrailing),
                in: RoundedRectangle(cornerRadius: 13)
            )
            .overlay(RoundedRectangle(cornerRadius: 13)
                .stroke(.white.opacity(0.52), lineWidth: 1))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(title), \(subtitle)")
    }
}

struct RDICompactAIMiniPlayer: View {
    @ObservedObject var radio: RadioPlayer
    let openAIMusic: () -> Void

    var body: some View {
        if let track = radio.currentAITrack {
            HStack(spacing: 10) {
                Button(action: openAIMusic) {
                    HStack(spacing: 10) {
                        Image(systemName: "music.note")
                            .font(.headline)
                            .foregroundStyle(.white)
                            .frame(width: 37, height: 37)
                            .background(RDITheme.violet, in: RoundedRectangle(cornerRadius: 10))

                        VStack(alignment: .leading, spacing: 2) {
                            Text(track.title)
                                .font(.subheadline.bold())
                                .lineLimit(1)
                            Text(track.artist)
                                .font(.caption)
                                .foregroundStyle(RDITheme.muted)
                                .lineLimit(1)
                        }
                    }
                }
                .buttonStyle(.plain)
                Spacer(minLength: 0)
                Button(action: radio.previousAITrack) {
                    Image(systemName: "backward.end.fill")
                }
                .disabled(!radio.canSkipAI)
                Button(action: radio.toggle) {
                    Image(systemName: radio.isPlaying ? "pause.fill" : "play.fill")
                }
                Button(action: radio.nextAITrack) {
                    Image(systemName: "forward.end.fill")
                }
                .disabled(!radio.canSkipAI)
            }
            .font(.system(size: 15, weight: .semibold))
            .foregroundStyle(.white)
            .buttonStyle(.plain)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(RDITheme.background)
            .overlay(alignment: .top) {
                Rectangle().fill(RDITheme.violet.opacity(0.7)).frame(height: 1)
            }
            .accessibilityElement(children: .contain)
        }
    }
}

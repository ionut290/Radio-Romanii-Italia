import AVFoundation
import MediaPlayer
import SwiftUI

enum RDITheme {
    static let background = Color(red: 0.015, green: 0.045, blue: 0.115)
    static let panel = Color(red: 0.04, green: 0.10, blue: 0.23)
    static let orange = Color(red: 1, green: 0.46, blue: 0.06)
    static let cyan = Color(red: 0.03, green: 0.77, blue: 1)
    static let violet = Color(red: 0.72, green: 0.18, blue: 1)
    static let muted = Color(red: 0.74, green: 0.79, blue: 0.90)
}

/// Animazione grafica: non pretende di rappresentare l'intensità reale dello stream.
struct RDIWaveform: View {
    var isPlaying: Bool
    var reduceMotion: Bool

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 15.0, paused: reduceMotion)) { timeline in
            Canvas(opaque: false) { context, size in
                let count = 49
                let spacing = size.width / CGFloat(count)
                let phase = isPlaying && !reduceMotion
                    ? timeline.date.timeIntervalSinceReferenceDate * 3.8 : 0
                for index in 0..<count {
                    let proportion = Double(index) / Double(count)
                    let envelope = 0.30 + 0.70 * abs(sin(proportion * .pi * 3.1))
                    let modulation = abs(sin(Double(index) * 0.65 + phase))
                    let height = CGFloat(5.0 + envelope * (12.0 + 35.0 * modulation))
                    let x = CGFloat(index) * spacing + spacing * 0.22
                    let rect = CGRect(x: x, y: (size.height - height) / 2,
                                      width: max(2, spacing * 0.52), height: height)
                    let color = Color(hue: 0.55 + proportion * 0.36,
                                      saturation: 0.98, brightness: 1.0)
                    context.fill(Path(roundedRect: rect, cornerRadius: spacing / 2),
                                 with: .color(color))
                }
            }
        }
        .frame(height: 58)
        .accessibilityHidden(true)
    }
}

struct RDIPhoneVolume: UIViewRepresentable {
    func makeUIView(context: Context) -> MPVolumeView {
        let slider = MPVolumeView(frame: .zero)
        slider.showsRouteButton = false
        slider.showsVolumeSlider = true
        slider.tintColor = UIColor.systemOrange
        return slider
    }

    func updateUIView(_ view: MPVolumeView, context: Context) {}
}

struct RDIPlayerHero: View {
    @ObservedObject var radio: RadioPlayer
    let reduceMotion: Bool
    @State private var glowing = false

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 25)
                .fill(
                    LinearGradient(
                        colors: [Color(red: 0.09, green: 0.07, blue: 0.26),
                                 Color(red: 0.04, green: 0.11, blue: 0.30),
                                 Color(red: 0.25, green: 0.03, blue: 0.31)],
                        startPoint: .topLeading, endPoint: .bottomTrailing
                    )
                )
            Circle()
                .fill(RDITheme.violet.opacity(glowing ? 0.34 : 0.16))
                .frame(width: 235, height: 235)
                .blur(radius: 68)
                .offset(x: glowing ? 130 : 70, y: glowing ? -70 : 70)
            Circle()
                .fill(RDITheme.cyan.opacity(glowing ? 0.23 : 0.10))
                .frame(width: 200, height: 200)
                .blur(radius: 64)
                .offset(x: glowing ? -130 : -60, y: 70)

            RDINeonLines(animated: !reduceMotion)
                .frame(height: 74)
                .opacity(0.55)
                .offset(y: 87)

            VStack(alignment: .leading, spacing: 11) {
                HStack(spacing: 8) {
                    Image(systemName: "dot.radiowaves.left.and.right")
                    Text("RADIO LIVE")
                        .tracking(1)
                    Spacer()
                    HStack(spacing: 5) {
                        Circle().fill(.red).frame(width: 7, height: 7)
                        Text("ON AIR")
                    }
                }
                .font(.system(size: 11, weight: .black))
                .foregroundStyle(.white)
                .padding(.horizontal, 11)
                .padding(.vertical, 8)
                .background(Color.red.opacity(0.77), in: Capsule())

                HStack(spacing: 12) {
                    ZStack {
                        Circle()
                            .fill(RDITheme.orange.opacity(0.27))
                            .frame(width: 93, height: 93)
                            .blur(radius: 22)
                        Image(systemName: "mic.fill")
                            .font(.system(size: 84, weight: .thin))
                            .foregroundStyle(
                                LinearGradient(colors: [.white, RDITheme.orange, RDITheme.violet],
                                               startPoint: .topLeading, endPoint: .bottomTrailing)
                            )
                            .shadow(color: RDITheme.orange.opacity(0.75), radius: 15)
                    }
                    .frame(width: 96)

                    VStack(alignment: .leading, spacing: 7) {
                        Text("Radio Românii\ndin Italia")
                            .font(.system(size: 24, weight: .black, design: .rounded))
                            .lineLimit(2)
                            .minimumScaleFactor(0.8)
                            .foregroundStyle(.white)
                        Text("Musica, notizie e comunità")
                            .font(.system(size: 13, weight: .medium))
                            .foregroundStyle(RDITheme.muted)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    Spacer(minLength: 0)
                }

                RDIWaveform(isPlaying: radio.isPlaying, reduceMotion: reduceMotion)

                HStack(spacing: 13) {
                    Image(systemName: "speaker.wave.2.fill")
                        .font(.headline)
                        .foregroundStyle(.white)
                        .accessibilityHidden(true)

                    RDIPhoneVolume()
                        .frame(height: 29)
                        .accessibilityLabel("Volume del dispositivo")

                    Button(action: radio.toggle) {
                        Image(systemName: radio.isPlaying ? "pause.fill" : "play.fill")
                            .font(.system(size: 27, weight: .bold))
                            .foregroundStyle(.white)
                            .frame(width: 65, height: 65)
                            .background(
                                LinearGradient(colors: [.orange, .red, RDITheme.violet],
                                               startPoint: .topLeading, endPoint: .bottomTrailing),
                                in: Circle()
                            )
                            .overlay(Circle().stroke(.white.opacity(0.55), lineWidth: 1))
                            .shadow(color: RDITheme.violet.opacity(0.9), radius: 15)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(radio.isPlaying ? "Metti in pausa la radio" : "Ascolta la radio")

                    Image(systemName: "headphones")
                        .font(.title3)
                        .foregroundStyle(.white.opacity(0.86))
                        .accessibilityHidden(true)
                }
                .padding(.top, 2)

                HStack {
                    Text(radio.isBuffering ? "Connessione in corso…" :
                         (radio.isPlaying ? "Stai ascoltando la diretta" : "Tocca Play per ascoltare"))
                    Spacer()
                    Image(systemName: "chart.bar.fill")
                        .foregroundStyle(radio.isPlaying ? RDITheme.orange : .gray)
                    Text("LIVE")
                        .foregroundStyle(.white)
                }
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(RDITheme.muted)

                if let error = radio.errorMessage {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
            }
            .padding(19)
        }
        .fixedSize(horizontal: false, vertical: true)
        .clipShape(RoundedRectangle(cornerRadius: 25))
        .overlay(
            RoundedRectangle(cornerRadius: 25)
                .stroke(
                    LinearGradient(
                        colors: [RDITheme.cyan, RDITheme.violet, RDITheme.orange],
                        startPoint: .topLeading, endPoint: .bottomTrailing
                    ),
                    lineWidth: 1.7
                )
        )
        .shadow(color: RDITheme.violet.opacity(0.39), radius: 16)
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(.easeInOut(duration: 3.2).repeatForever(autoreverses: true)) {
                glowing = true
            }
        }
    }
}

struct RDIQuickTile: View {
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @AppStorage("rdi.reduceAnimations") private var reduceAnimations = false
    @State private var glow = false
    let title: String
    let subtitle: String
    let symbol: String
    let colors: [Color]
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                RoundedRectangle(cornerRadius: 19)
                    .fill(LinearGradient(colors: colors, startPoint: .topLeading,
                                         endPoint: .bottomTrailing))
                Circle()
                    .fill(.white.opacity(0.18))
                    .frame(width: 86, height: 86)
                    .blur(radius: 22)
                    .offset(x: 43, y: -42)
                VStack(spacing: 7) {
                    Image(systemName: symbol)
                        .font(.system(size: 31, weight: .bold))
                        .foregroundStyle(.white)
                        .shadow(color: .white.opacity(0.7), radius: 10)
                    Text(title)
                        .font(.system(size: 12, weight: .black, design: .rounded))
                        .foregroundStyle(.white)
                        .lineLimit(2)
                        .minimumScaleFactor(0.72)
                        .multilineTextAlignment(.center)
                    Text(subtitle)
                        .font(.system(size: 9, weight: .medium))
                        .foregroundStyle(.white.opacity(0.95))
                        .lineLimit(2)
                        .minimumScaleFactor(0.75)
                        .multilineTextAlignment(.center)
                }
                .padding(.horizontal, 5)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 130)
            .clipShape(RoundedRectangle(cornerRadius: 19))
            .overlay(
                RoundedRectangle(cornerRadius: 19)
                    .stroke(.white.opacity(glow ? 0.95 : 0.5), lineWidth: glow ? 1.9 : 1)
            )
            .shadow(color: (colors.first ?? .clear).opacity(glow ? 0.86 : 0.42),
                    radius: glow ? 18 : 8)
            .scaleEffect(glow ? 1.016 : 1)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(title). \(subtitle)")
        .onAppear {
            guard !reduceAnimations && !systemReduceMotion else { return }
            withAnimation(.easeInOut(duration: 2.5).repeatForever(autoreverses: true)) {
                glow = true
            }
        }
    }
}

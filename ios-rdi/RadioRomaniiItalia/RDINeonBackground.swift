import SwiftUI

/// Fondale neon ispirato alla home RDI approvata.
struct RDINeonBackground: View {
    var animated: Bool
    @State private var phase = false

    var body: some View {
        GeometryReader { proxy in
            ZStack {
                LinearGradient(
                    colors: [
                        Color(red: 0.02, green: 0.06, blue: 0.20),
                        RDITheme.background,
                        Color(red: 0.08, green: 0.025, blue: 0.19)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )

                Circle()
                    .fill(RDITheme.cyan.opacity(phase ? 0.26 : 0.13))
                    .frame(width: 280, height: 280)
                    .blur(radius: 85)
                    .offset(x: phase ? proxy.size.width * 0.32 : -proxy.size.width * 0.18,
                            y: phase ? -proxy.size.height * 0.2 : -proxy.size.height * 0.32)

                Circle()
                    .fill(RDITheme.violet.opacity(phase ? 0.26 : 0.17))
                    .frame(width: 300, height: 300)
                    .blur(radius: 90)
                    .offset(x: phase ? -proxy.size.width * 0.35 : proxy.size.width * 0.2,
                            y: phase ? proxy.size.height * 0.35 : proxy.size.height * 0.2)

                Circle()
                    .fill(RDITheme.orange.opacity(phase ? 0.17 : 0.09))
                    .frame(width: 195, height: 195)
                    .blur(radius: 70)
                    .offset(x: -proxy.size.width * 0.3,
                            y: phase ? -proxy.size.height * 0.16 : proxy.size.height * 0.12)
            }
            .frame(width: proxy.size.width, height: proxy.size.height)
        }
        .ignoresSafeArea()
        .allowsHitTesting(false)
        .onAppear {
            guard animated else { return }
            withAnimation(.easeInOut(duration: 6.5).repeatForever(autoreverses: true)) {
                phase = true
            }
        }
    }
}

/// Tre curve luminose evocano il movimento di una trasmissione radiofonica.
struct RDINeonLines: View {
    var animated: Bool
    @State private var highlighted = false

    var body: some View {
        GeometryReader { geo in
            ZStack {
                ForEach(0..<3, id: \.self) { index in
                    Path { path in
                        let height = geo.size.height
                        let width = geo.size.width
                        path.move(to: CGPoint(x: -10, y: height * (0.55 + Double(index) * 0.12)))
                        path.addCurve(
                            to: CGPoint(x: width + 10, y: height * (0.5 - Double(index) * 0.08)),
                            control1: CGPoint(x: width * 0.36, y: height * (0.04 + Double(index) * 0.15)),
                            control2: CGPoint(x: width * 0.65, y: height * (0.95 - Double(index) * 0.07))
                        )
                    }
                    .stroke(
                        [RDITheme.cyan, RDITheme.violet, RDITheme.orange][index]
                            .opacity(highlighted ? 0.75 : 0.33),
                        style: StrokeStyle(lineWidth: index == 2 ? 2.6 : 2,
                                           lineCap: .round)
                    )
                    .shadow(color: [RDITheme.cyan, RDITheme.violet, RDITheme.orange][index],
                            radius: highlighted ? 14 : 5)
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onAppear {
            guard animated else { return }
            withAnimation(.easeInOut(duration: 2.4).repeatForever(autoreverses: true)) {
                highlighted = true
            }
        }
    }
}

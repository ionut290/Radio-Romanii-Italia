import SafariServices
import SwiftUI

private enum RDITab: String, CaseIterable, Identifiable {
    case home = "Home"
    case radio = "Radio"
    case aiMusic = "AI Music"
    case news = "Notizie"
    case community = "Comunità"
    case settings = "Impostazioni"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .home: return "house.fill"
        case .radio: return "dot.radiowaves.left.and.right"
        case .aiMusic: return "music.note"
        case .news: return "newspaper.fill"
        case .community: return "person.2.fill"
        case .settings: return "gearshape.fill"
        }
    }
}

private enum RDINewsFilter: String, CaseIterable, Identifiable {
    case all = "Tutte"
    case diaspora = "Diaspora"
    case italy = "Italia"
    case romania = "Romania"
    case culture = "Cultura"
    case events = "Eventi"

    var id: String { rawValue }

    func includes(_ article: RadioNewsArticle) -> Bool {
        if self == .all { return true }
        let category = (article.category ?? "").folding(
            options: [.diacriticInsensitive, .caseInsensitive], locale: Locale(identifier: "it_IT")
        ).lowercased()
        let title = article.title.folding(
            options: [.diacriticInsensitive, .caseInsensitive], locale: Locale(identifier: "it_IT")
        ).lowercased()
        switch self {
        case .all: return true
        case .diaspora: return category.contains("diaspora")
        case .italy: return category.contains("italia")
        case .romania: return category.contains("romania")
        case .culture: return category.contains("cultur") || title.contains("cultur")
        case .events: return category.contains("event") || title.contains("festival") || title.contains("evento")
        }
    }
}

private struct RDIWebPage: Identifiable {
    let id = UUID()
    let url: URL
}

private struct RDIInAppBrowser: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        let controller = SFSafariViewController(url: url)
        controller.dismissButtonStyle = .done
        controller.preferredControlTintColor = UIColor.systemOrange
        return controller
    }

    func updateUIViewController(_ controller: SFSafariViewController, context: Context) {}
}

struct RadioHomeView: View {
    @EnvironmentObject private var radio: RadioPlayer
    @Environment(\.openURL) private var openURL
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @StateObject private var news = RadioNewsStore()
    @StateObject private var aiMusic = RDIAIMusicStore()
    @AppStorage("rdi.reduceAnimations") private var reduceAnimations = false

    @State private var tab: RDITab = .home
    @State private var webPage: RDIWebPage?

    private let site = "https://radioromanii.duckdns.org"
    private let podcast = "https://www.youtube.com/channel/UCmvtZ9q5gOoFJEm_Q9UaOuw/podcasts"

    private var noMotion: Bool { reduceAnimations || systemReduceMotion }

    var body: some View {
        ZStack {
            RDINeonBackground(animated: !noMotion)

            VStack(spacing: 0) {
                header
                ScrollView {
                    VStack(alignment: .leading, spacing: 13) {
                        pageContent
                    }
                    .frame(maxWidth: 720)
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 14)
                    .padding(.top, 14)
                    .padding(.bottom, 22)
                }
                .refreshable { await news.refresh() }
                if tab != .aiMusic {
                    RDICompactAIMiniPlayer(radio: radio) { tab = .aiMusic }
                }
                bottomBar
            }
        }
        .preferredColorScheme(.dark)
        .tint(RDITheme.orange)
        .sheet(item: $webPage) { target in
            RDIInAppBrowser(url: target.url)
                .ignoresSafeArea()
        }
        .task { await news.refresh() }
    }

    private var header: some View {
        HStack(spacing: 10) {
            ZStack {
                RoundedRectangle(cornerRadius: 13)
                    .fill(
                        LinearGradient(colors: [RDITheme.orange, .red],
                                       startPoint: .topLeading, endPoint: .bottomTrailing)
                    )
                    .frame(width: 45, height: 45)
                Image(systemName: "antenna.radiowaves.left.and.right")
                    .font(.title2.weight(.heavy))
                    .foregroundStyle(.white)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text("RDI")
                    .font(.system(size: 27, weight: .black, design: .rounded))
                    .italic()
                    .foregroundStyle(.white)
                Text("Radio Românii din Italia")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(RDITheme.muted)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            }
            Spacer(minLength: 3)

            Button {
                tab = .settings
            } label: {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 20))
                    .foregroundStyle(.white)
                    .frame(width: 43, height: 43)
            }
            .accessibilityLabel("Apri impostazioni")
        }
        .padding(.horizontal, 16)
        .padding(.top, 6)
        .padding(.bottom, 8)
        .background(RDITheme.background)
    }

    @ViewBuilder private var pageContent: some View {
        switch tab {
        case .home:
            RDICompactRadioPlayer(radio: radio, reduceMotion: noMotion)
            newsList(isCompact: true)
        case .radio:
            Text("Ascolta RDI")
                .font(.title.bold())
                .foregroundStyle(.white)
            RDICompactRadioPlayer(radio: radio, reduceMotion: noMotion)
            infoCard(title: "RDI AI MUSIC Spotlight",
                     detail: "Scopri le classifiche, ascolta i brani originali approvati e partecipa alla community.",
                     symbol: "music.note.list", button: "Scopri i brani") {
                tab = .aiMusic
            }
        case .aiMusic:
            RDIAIMusicView(store: aiMusic)
        case .news:
            newsList(isCompact: false)
        case .community:
            Text("La nostra comunità")
                .font(.title.bold())
                .foregroundStyle(.white)
            infoCard(title: "Comunità dei romeni in Italia",
                     detail: "Storie, iniziative, esperienze e incontri della nostra comunità.",
                     symbol: "person.3.fill", button: "Apri la comunità") {
                openInApp("\(site)/comunitate.html")
            }
            infoCard(title: "Eventi",
                     detail: "Scopri gli appuntamenti e le iniziative culturali.",
                     symbol: "calendar", button: "Scopri gli eventi") {
                openInApp("\(site)/evenimente.html")
            }
            infoCard(title: "Podcast RDI su YouTube",
                     detail: "Trova gli episodi e le rubriche nel canale YouTube della radio.",
                     symbol: "mic.fill", button: "Guarda i podcast") {
                openExternalMedia(podcast)
            }
        case .settings:
            settingsContent
        }
    }

    private func newsList(isCompact: Bool) -> some View {
        RDINewsList(
            store: news,
            compact: isCompact,
            onShowAll: { tab = .news },
            onOpenArticle: { url in
                webPage = RDIWebPage(url: url)
            }
        )
    }

    private var settingsContent: some View {
        VStack(alignment: .leading, spacing: 17) {
            Text("Impostazioni")
                .font(.title.bold())
                .foregroundStyle(.white)

            Toggle(isOn: $reduceAnimations) {
                Label("Riduci le animazioni", systemImage: "sparkles")
                    .font(.headline)
            }
            .tint(RDITheme.orange)
            .padding(18)
            .background(RDITheme.panel, in: RoundedRectangle(cornerRadius: 17))

            Text("Gli effetti grafici non modificano l'audio della radio.")
                .font(.footnote)
                .foregroundStyle(RDITheme.muted)

            infoCard(title: "Sito ufficiale RDI",
                     detail: "Notizie, dirette e comunità.",
                     symbol: "globe", button: "Apri il sito") {
                openInApp("\(site)/")
            }
        }
    }

    private func infoCard(title: String, detail: String, symbol: String,
                          button: String, action: @escaping () -> Void) -> some View {
        VStack(alignment: .leading, spacing: 13) {
            Label(title, systemImage: symbol)
                .font(.headline)
                .foregroundStyle(.white)
            Text(detail)
                .font(.subheadline)
                .foregroundStyle(RDITheme.muted)
            Button(action: action) {
                HStack {
                    Text(button)
                    Spacer()
                    Image(systemName: "arrow.up.right")
                }
                .font(.subheadline.bold())
                .foregroundStyle(RDITheme.orange)
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RDITheme.panel, in: RoundedRectangle(cornerRadius: 18))
        .overlay(RoundedRectangle(cornerRadius: 18)
            .stroke(RDITheme.cyan.opacity(0.24), lineWidth: 1))
    }

    private var bottomBar: some View {
        HStack(spacing: 0) {
            ForEach(RDITab.allCases.filter { $0 != .settings }) { item in
                Button {
                    withAnimation(noMotion ? nil : .easeInOut(duration: 0.19)) {
                        tab = item
                    }
                } label: {
                    VStack(spacing: 5) {
                        Image(systemName: item.icon)
                            .font(.system(size: 20, weight: .semibold))
                            .frame(height: 23)
                        Text(item.rawValue)
                            .font(.system(size: 10, weight: tab == item ? .bold : .medium))
                            .lineLimit(1)
                            .minimumScaleFactor(0.72)
                    }
                    .foregroundStyle(tab == item ? RDITheme.orange : RDITheme.muted)
                    .frame(maxWidth: .infinity)
                    .frame(height: 57)
                    .background(
                        tab == item ? RDITheme.orange.opacity(0.1) : .clear,
                        in: RoundedRectangle(cornerRadius: 15)
                    )
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(tab == item ? [.isSelected] : [])
            }
        }
        .padding(.horizontal, 9)
        .padding(.top, 9)
        .padding(.bottom, 3)
        .background(
            RDITheme.background
                .overlay(alignment: .top) {
                    Rectangle().fill(RDITheme.cyan.opacity(0.27)).frame(height: 1)
                }
        )
    }

    private func openExternalMedia(_ address: String) {
        guard let url = URL(string: address), url.scheme == "https" else { return }
        radio.pause()
        openURL(url)
    }

    private func openInApp(_ address: String, pauseRadio: Bool = false) {
        guard let url = URL(string: address), url.scheme == "https" else { return }
        if pauseRadio { radio.pause() }
        webPage = RDIWebPage(url: url)
    }
}

private struct RDINewsList: View {
    @ObservedObject var store: RadioNewsStore
    let compact: Bool
    let onShowAll: () -> Void
    let onOpenArticle: (URL) -> Void
    @State private var filter: RDINewsFilter = .all

    private var visible: [RadioNewsArticle] {
        let filtered = store.articles.filter { filter.includes($0) }
        return compact ? Array(filtered.prefix(2)) : Array(filtered.prefix(50))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Ultime notizie", systemImage: "newspaper.fill")
                    .font(.system(size: 21, weight: .bold))
                    .foregroundStyle(.white)
                Spacer()
                if compact {
                    Button("Vedi tutto") { onShowAll() }
                        .font(.subheadline.bold())
                        .foregroundStyle(RDITheme.orange)
                } else {
                    Button {
                        Task { await store.refresh() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .font(.headline)
                    }
                    .accessibilityLabel("Aggiorna notizie")
                }
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(RDINewsFilter.allCases) { item in
                        Button {
                            filter = item
                        } label: {
                            Text(item.rawValue)
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundStyle(filter == item ? .white : RDITheme.muted)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 9)
                                .background(
                                    filter == item ? RDITheme.orange :
                                        RDITheme.panel,
                                    in: Capsule()
                                )
                                .overlay(Capsule()
                                    .stroke(.white.opacity(0.24), lineWidth: 0.7))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            if store.isLoading && store.articles.isEmpty {
                ProgressView("Caricamento delle notizie…")
                    .foregroundStyle(.white)
                    .padding(22)
            } else if visible.isEmpty {
                Text(store.errorMessage ?? "Non ci sono notizie in questa categoria.")
                    .font(.subheadline)
                    .foregroundStyle(RDITheme.muted)
                    .padding(18)
            } else {
                LazyVStack(spacing: 10) {
                    ForEach(visible) { article in
                        newsCard(article)
                    }
                }
            }
        }
    }

    private func newsCard(_ article: RadioNewsArticle) -> some View {
        Button {
            guard let url = article.destination else { return }
            onOpenArticle(url)
        } label: {
            HStack(spacing: 11) {
                ZStack {
                    RoundedRectangle(cornerRadius: 12)
                        .fill(RDITheme.panel)
                    if let imageURL = article.imageURL {
                        AsyncImage(url: imageURL) { phase in
                            switch phase {
                            case .success(let image): image.resizable().scaledToFill()
                            default:
                                Image(systemName: "newspaper.fill")
                                    .resizable().scaledToFit().padding(24)
                                    .foregroundStyle(RDITheme.cyan)
                            }
                        }
                        .clipped()
                    } else {
                        Image(systemName: "newspaper.fill")
                            .font(.largeTitle)
                            .foregroundStyle(RDITheme.cyan)
                    }
                }
                .frame(width: 104, height: 100)
                .clipShape(RoundedRectangle(cornerRadius: 12))

                VStack(alignment: .leading, spacing: 6) {
                    Text((article.category ?? "NOTIZIE").uppercased())
                        .font(.system(size: 10, weight: .black))
                        .foregroundStyle(RDITheme.orange)
                    Text(store.italianTitle(for: article))
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(.white)
                        .lineLimit(3)
                        .multilineTextAlignment(.leading)
                    HStack(spacing: 5) {
                        Text(article.source ?? "RDI")
                        if let date = article.shortDate {
                            Text("·")
                            Text(date)
                        }
                    }
                    .font(.system(size: 10))
                    .foregroundStyle(RDITheme.muted)
                    .lineLimit(1)
                }
                Spacer(minLength: 0)
                Image(systemName: "chevron.right")
                    .font(.caption.bold())
                    .foregroundStyle(RDITheme.cyan)
            }
            .padding(9)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                LinearGradient(colors: [RDITheme.panel,
                                         Color(red: 0.025, green: 0.065, blue: 0.16)],
                               startPoint: .topLeading, endPoint: .bottomTrailing),
                in: RoundedRectangle(cornerRadius: 17)
            )
            .overlay(RoundedRectangle(cornerRadius: 17)
                .stroke(RDITheme.cyan.opacity(0.39), lineWidth: 0.9))
        }
        .buttonStyle(.plain)
        .accessibilityHint("Apri l'articolo")
    }
}

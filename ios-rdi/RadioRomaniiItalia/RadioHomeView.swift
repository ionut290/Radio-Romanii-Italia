import SwiftUI
import SafariServices

private enum NewsFilter: String, CaseIterable {
    case all = "Toate"
    case diaspora = "Diaspora"
    case italy = "Italia"
    case romania = "România"

    func includes(_ article: RadioNewsArticle) -> Bool {
        let category = (article.category ?? "").folding(
            options: [.diacriticInsensitive, .caseInsensitive],
            locale: Locale(identifier: "ro_RO")
        ).lowercased()
        switch self {
        case .all: return true
        case .diaspora: return category.contains("diaspora") || category.contains("comunit")
        case .italy: return category.contains("italia")
        case .romania: return category.contains("romania")
        }
    }
}

private struct ArticleDestination: Identifiable {
    let id = UUID()
    let url: URL
}

private struct InAppArticleBrowser: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        let browser = SFSafariViewController(url: url)
        browser.dismissButtonStyle = .done
        return browser
    }

    func updateUIViewController(_ controller: SFSafariViewController, context: Context) {}
}

struct RadioHomeView: View {
    @EnvironmentObject private var radio: RadioPlayer
    @StateObject private var news = RadioNewsStore()
    @State private var filter: NewsFilter = .all
    @State private var articleDestination: ArticleDestination?

    private let orange = Color(red: 1.0, green: 0.54, blue: 0.17)
    private let navy = Color(red: 0.06, green: 0.10, blue: 0.20)

    private var filteredArticles: [RadioNewsArticle] {
        Array(news.articles.filter { filter.includes($0) }.prefix(12))
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    topBar
                    radioCard
                    newsSection
                    communityFooter
                }
                .frame(maxWidth: 680)
                .frame(maxWidth: .infinity)
                .padding(.horizontal, 18)
                .padding(.top, 14)
                .padding(.bottom, 26)
            }
            .background(Color(uiColor: .systemGroupedBackground))
            .safeAreaInset(edge: .bottom, spacing: 0) {
                compactPlayer
            }
            .refreshable {
                await news.refresh()
            }
            .task {
                await news.refresh()
            }
            .sheet(item: $articleDestination) { destination in
                InAppArticleBrowser(url: destination.url)
                    .ignoresSafeArea()
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private var topBar: some View {
        HStack(spacing: 10) {
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(orange)
                    .frame(width: 46, height: 46)
                Image(systemName: "antenna.radiowaves.left.and.right")
                    .font(.title3.weight(.bold))
                    .foregroundStyle(.white)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text("RDI")
                    .font(.title2.weight(.heavy))
                    .foregroundStyle(navy)
                Text("Radio Românii din Italia")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            HStack(spacing: 5) {
                Circle()
                    .fill(.red)
                    .frame(width: 7, height: 7)
                Text("ON AIR")
                    .font(.caption.weight(.bold))
            }
            .foregroundStyle(navy)
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(.white, in: Capsule())
            .accessibilityLabel("Radio în direct")
        }
    }

    private var radioCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Label("ASCULTĂ LIVE", systemImage: "dot.radiowaves.left.and.right")
                    .font(.caption.weight(.bold))
                    .tracking(1.1)
                    .foregroundStyle(orange)
                Spacer()
                Image(systemName: "waveform")
                    .font(.title2)
                    .foregroundStyle(.white.opacity(0.75))
                    .accessibilityHidden(true)
            }

            Text("Muzică, știri\nși comunitate")
                .font(.system(size: 30, weight: .bold, design: .rounded))
                .foregroundStyle(.white)
                .fixedSize(horizontal: false, vertical: true)

            Text(radio.isBuffering ? "Se conectează la emisie..." :
                    (radio.isPlaying ? "Acum asculți Radio Românii" : "Radioul tău, oriunde te-ai afla"))
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.75))

            Button(action: radio.toggle) {
                HStack(spacing: 12) {
                    Image(systemName: radio.isPlaying ? "pause.fill" : "play.fill")
                        .font(.title3.weight(.bold))
                    Text(radio.isPlaying ? "Pauză" : "Pornește radioul")
                        .font(.headline)
                    Spacer()
                    Image(systemName: "headphones")
                }
                .foregroundStyle(navy)
                .padding(17)
                .background(orange, in: RoundedRectangle(cornerRadius: 15))
            }
            .buttonStyle(.plain)
            .accessibilityHint("Pornește sau oprește transmisia live")

            if let error = radio.errorMessage {
                Label(error, systemImage: "exclamationmark.triangle")
                    .font(.footnote)
                    .foregroundStyle(.white)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(22)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            LinearGradient(
                colors: [navy, Color(red: 0.13, green: 0.20, blue: 0.34)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 24)
        )
    }

    private var newsSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Ultimele știri")
                        .font(.title2.weight(.bold))
                        .foregroundStyle(.primary)
                    Text("Noutăți din Italia, România și diaspora")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button {
                    Task { await news.refresh() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.headline)
                        .frame(width: 42, height: 42)
                        .background(.white, in: Circle())
                }
                .accessibilityLabel("Actualizează știrile")
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 9) {
                    ForEach(NewsFilter.allCases, id: \.self) { item in
                        Button {
                            filter = item
                        } label: {
                            Text(item.rawValue)
                                .font(.subheadline.weight(.semibold))
                                .padding(.horizontal, 15)
                                .padding(.vertical, 10)
                                .foregroundStyle(filter == item ? Color.white : Color.primary)
                                .background(
                                    filter == item ? navy : Color(uiColor: .secondarySystemGroupedBackground),
                                    in: Capsule()
                                )
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.vertical, 2)
            }

            if news.isLoading && news.articles.isEmpty {
                ProgressView("Se încarcă știrile...")
                    .frame(maxWidth: .infinity)
                    .padding(36)
            } else if let error = news.errorMessage, news.articles.isEmpty {
                ContentUnavailableViewFallback(message: error)
            } else if filteredArticles.isEmpty {
                ContentUnavailableViewFallback(message: "Nu există încă știri în această categorie.")
            } else {
                LazyVStack(spacing: 12) {
                    ForEach(filteredArticles) { article in
                        newsCard(article)
                    }
                }
            }
        }
    }

    private func newsCard(_ article: RadioNewsArticle) -> some View {
        Button {
            guard let url = article.destination else { return }
            articleDestination = ArticleDestination(url: url)
        } label: {
            HStack(alignment: .top, spacing: 13) {
                newsThumbnail(article)
                VStack(alignment: .leading, spacing: 7) {
                    Text((article.category ?? "Știri").uppercased())
                        .font(.system(size: 10, weight: .bold))
                        .tracking(0.7)
                        .foregroundStyle(orange)

                    Text(article.title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(3)
                        .multilineTextAlignment(.leading)

                    HStack(spacing: 5) {
                        Text(article.source ?? "RDI")
                        if let date = article.shortDate {
                            Text("·")
                            Text(date)
                        }
                    }
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                }
                Spacer(minLength: 0)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(uiColor: .secondarySystemGroupedBackground),
                        in: RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
        .accessibilityHint("Deschide articolul")
    }

    @ViewBuilder
    private func newsThumbnail(_ article: RadioNewsArticle) -> some View {
        if let url = article.imageURL {
            AsyncImage(url: url) { phase in
                if case .success(let image) = phase {
                    image.resizable().scaledToFill()
                } else {
                    thumbnailPlaceholder
                }
            }
            .frame(width: 98, height: 96)
            .clipShape(RoundedRectangle(cornerRadius: 11))
        } else {
            thumbnailPlaceholder
                .frame(width: 98, height: 96)
                .clipShape(RoundedRectangle(cornerRadius: 11))
        }
    }

    private var thumbnailPlaceholder: some View {
        ZStack {
            Color(red: 0.93, green: 0.94, blue: 0.96)
            Image(systemName: "newspaper.fill")
                .font(.title2)
                .foregroundStyle(navy.opacity(0.45))
        }
    }

    private var communityFooter: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Comunitatea noastră", systemImage: "person.3.fill")
                .font(.headline)
            Text("Povești, evenimente și informații pentru românii din Italia.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Link(destination: URL(string: "https://radioromanii.duckdns.org/")!) {
                HStack {
                    Text("Explorează site-ul RDI")
                    Spacer()
                    Image(systemName: "arrow.up.right")
                }
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(orange)
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(uiColor: .secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 18))
    }

    private var compactPlayer: some View {
        HStack(spacing: 12) {
            Image(systemName: "antenna.radiowaves.left.and.right")
                .font(.title3.weight(.bold))
                .foregroundStyle(orange)
                .frame(width: 40, height: 40)
                .background(navy, in: RoundedRectangle(cornerRadius: 10))

            VStack(alignment: .leading, spacing: 3) {
                Text("Radio Românii din Italia")
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(1)
                Text(radio.isBuffering ? "Conectare..." : (radio.isPlaying ? "În direct" : "Atinge pentru a asculta"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button(action: radio.toggle) {
                Image(systemName: radio.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title3.weight(.bold))
                    .foregroundStyle(.white)
                    .frame(width: 46, height: 46)
                    .background(orange, in: Circle())
            }
            .accessibilityLabel(radio.isPlaying ? "Pauză" : "Pornește radioul")
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity)
        .background(.regularMaterial)
    }
}

private struct ContentUnavailableViewFallback: View {
    let message: String

    var body: some View {
        VStack(spacing: 9) {
            Image(systemName: "wifi.exclamationmark")
                .font(.title)
                .foregroundStyle(.secondary)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(30)
    }
}

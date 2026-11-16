import Foundation
import SwiftUI

struct RadioNewsFeed: Decodable {
    let updatedAt: String?
    let items: [RadioNewsArticle]

    enum CodingKeys: String, CodingKey {
        case updatedAt = "updated_at"
        case items
    }
}

struct RadioNewsArticle: Decodable, Identifiable {
    let articleID: String?
    let dailyThought: Bool?
    let date: String?
    let category: String?
    let title: String
    let url: String?
    let source: String?
    let published: String?
    let summary: String?
    let image: String?

    enum CodingKeys: String, CodingKey {
        case articleID = "id"
        case dailyThought = "daily_thought"
        case date, category, title, url, source, published, summary, image
    }

    var id: String { url ?? articleID ?? (title + "|" + (published ?? "")) }

    var destination: URL? {
        if let url, let link = URL(string: url),
           ["https", "http"].contains(link.scheme ?? "") {
            return link
        }
        // Gli articoli originali RDI senza URL esterno si aprono sul sito.
        guard let articleID,
              var components = URLComponents(string: "https://radioromanii.duckdns.org/") else {
            return nil
        }
        components.queryItems = [URLQueryItem(name: "articolo", value: articleID)]
        return components.url
    }

    var imageURL: URL? {
        guard let image, !image.isEmpty, !image.lowercased().contains(".svg") else {
            return nil
        }
        if image.hasPrefix("https://") { return URL(string: image) }
        if image.hasPrefix("./") || image.hasPrefix("/") {
            return URL(string: image, relativeTo: URL(string: "https://radioromanii.duckdns.org/"))?.absoluteURL
        }
        return nil
    }

    static func parsedDate(_ value: String?) -> Date? {
        guard let value else { return nil }
        let parser = ISO8601DateFormatter()
        parser.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = parser.date(from: value) { return date }
        parser.formatOptions = [.withInternetDateTime]
        return parser.date(from: value)
    }

    var shortDate: String? {
        guard let date = Self.parsedDate(published) else { return nil }
        return date.formatted(date: .abbreviated, time: .omitted)
    }
}

private struct RDITranslatedHeadline: Decodable {
    let title: String?
}

private struct RDITranslatedArticle: Decodable {
    let original: RDITranslatedHeadline?
    let it: RDITranslatedHeadline?
}

private struct RDITranslationsResponse: Decodable {
    let items: [String: RDITranslatedArticle]
}

@MainActor
final class RadioNewsStore: ObservableObject {
    @Published private(set) var articles: [RadioNewsArticle] = []
    @Published private(set) var italianTitles: [String: String] = [:]
    @Published private(set) var lastUpdated: Date?
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?

    // Il sito ufficiale è la fonte principale; GitHub è solo un fallback.
    private let siteBase = "https://radioromanii.duckdns.org"
    private let githubBase = "https://raw.githubusercontent.com/ionut290/Radio-Romanii-Italia/main"

    func italianTitle(for article: RadioNewsArticle) -> String {
        italianTitles[article.title] ?? article.title
    }

    private func sources(for path: String) -> [URL] {
        [siteBase, githubBase].compactMap { URL(string: $0 + "/" + path) }
    }

    private func request(for url: URL) -> URLRequest {
        // Anche cache intermedie e CDN non devono mantenere notizie vecchie.
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        components?.queryItems = [URLQueryItem(
            name: "rdi_refresh",
            value: String(Int(Date().timeIntervalSince1970))
        )]
        var request = URLRequest(url: components?.url ?? url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("no-cache, no-store", forHTTPHeaderField: "Cache-Control")
        request.timeoutInterval = 15
        return request
    }

    private func loadFeed(_ path: String) async -> RadioNewsFeed? {
        for endpoint in sources(for: path) {
            do {
                let (data, response) = try await URLSession.shared.data(for: request(for: endpoint))
                guard let response = response as? HTTPURLResponse,
                      (200...299).contains(response.statusCode) else { continue }
                let feed = try JSONDecoder().decode(RadioNewsFeed.self, from: data)
                if !feed.items.isEmpty { return feed }
            } catch {
                // La seconda origine viene tentata soltanto in caso di errore.
                continue
            }
        }
        return nil
    }

    private func loadItalianTitles() async {
        for endpoint in sources(for: "news-translations.json") {
            do {
                let (data, response) = try await URLSession.shared.data(for: request(for: endpoint))
                guard let response = response as? HTTPURLResponse,
                      (200...299).contains(response.statusCode) else { continue }
                let translated = try JSONDecoder().decode(RDITranslationsResponse.self, from: data)
                var titles: [String: String] = [:]
                for item in translated.items.values {
                    guard let original = item.original?.title,
                          let italian = item.it?.title, !italian.isEmpty else { continue }
                    titles[original] = italian
                }
                italianTitles = titles
                return
            } catch {
                continue
            }
        }
    }

    func refresh() async {
        guard !isLoading else { return }
        isLoading = true
        defer { isLoading = false }

        // Stessa composizione usata dal sito: notizie, redazione e pensiero odierno.
        let newsFeed = await loadFeed("news.json")
        let editorialFeed = await loadFeed("editorial.json")
        let thoughtFeed = await loadFeed("data/daily-thought.json")

        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        dateFormatter.timeZone = TimeZone(identifier: "Europe/Rome")
        let today = dateFormatter.string(from: Date())

        let editorial = editorialFeed?.items ?? []
        let thoughts = (thoughtFeed?.items ?? []).filter {
            $0.dailyThought == true && $0.date == today
        }
        let external = newsFeed?.items ?? []
        let now = Date()

        let ordered = (editorial + external + thoughts)
            .filter { article in
                guard !article.title.isEmpty, article.destination != nil,
                      let published = RadioNewsArticle.parsedDate(article.published) else {
                    return false
                }
                let age = now.timeIntervalSince(published)
                return age >= 0 && age < 48 * 60 * 60
            }
            .sorted {
                (RadioNewsArticle.parsedDate($0.published) ?? .distantPast) >
                (RadioNewsArticle.parsedDate($1.published) ?? .distantPast)
            }

        if !ordered.isEmpty {
            var seen = Set<String>()
            articles = ordered.filter { seen.insert($0.id).inserted }
            lastUpdated = [newsFeed, editorialFeed, thoughtFeed]
                .compactMap { RadioNewsArticle.parsedDate($0?.updatedAt) }
                .max()
            errorMessage = nil
            await loadItalianTitles()
        } else {
            errorMessage = "Impossibile aggiornare le notizie. Riprova tra poco."
        }
    }
}

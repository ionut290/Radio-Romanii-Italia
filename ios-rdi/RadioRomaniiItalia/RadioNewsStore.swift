import Foundation
import SwiftUI

struct RadioNewsFeed: Decodable {
    let items: [RadioNewsArticle]
}

struct RadioNewsArticle: Decodable, Identifiable {
    let category: String?
    let title: String
    let url: String
    let source: String?
    let published: String?
    let summary: String?
    let image: String?

    var id: String { url }

    var destination: URL? {
        guard let link = URL(string: url), ["https", "http"].contains(link.scheme ?? "") else {
            return nil
        }
        return link
    }

    var imageURL: URL? {
        guard let image, image.hasPrefix("https://"),
              !image.lowercased().contains(".svg") else { return nil }
        return URL(string: image)
    }

    var shortDate: String? {
        guard let published else { return nil }
        let formatter = ISO8601DateFormatter()
        let date = formatter.date(from: published)
            ?? ISO8601DateFormatter().date(from: published.replacingOccurrences(of: "+00:00", with: "Z"))
        guard let date else { return nil }
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
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?

    // Prima sursă: site-ul RDI. GitHub este rezervă când site-ul nu răspunde.
    private let sources = [
        URL(string: "https://radioromanii.duckdns.org/news.json")!,
        URL(string: "https://raw.githubusercontent.com/ionut290/Radio-Romanii-Italia/main/news.json")!
    ]

    func italianTitle(for article: RadioNewsArticle) -> String {
        italianTitles[article.title] ?? article.title
    }

    private func loadItalianTitles() async {
        let endpoints = [
            URL(string: "https://radioromanii.duckdns.org/news-translations.json")!,
            URL(string: "https://raw.githubusercontent.com/ionut290/Radio-Romanii-Italia/main/news-translations.json")!
        ]
        for endpoint in endpoints {
            do {
                var request = URLRequest(url: endpoint)
                request.cachePolicy = .reloadIgnoringLocalCacheData
                request.timeoutInterval = 10
                let (data, response) = try await URLSession.shared.data(for: request)
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

        for url in sources {
            do {
                var request = URLRequest(url: url)
                request.cachePolicy = .reloadIgnoringLocalCacheData
                request.timeoutInterval = 15

                let (data, response) = try await URLSession.shared.data(for: request)
                guard let response = response as? HTTPURLResponse,
                      (200...299).contains(response.statusCode) else { continue }

                let feed = try JSONDecoder().decode(RadioNewsFeed.self, from: data)
                let valid = feed.items.filter { !$0.title.isEmpty && $0.destination != nil }
                if !valid.isEmpty {
                    // Elimina gli eventuali duplicati mantenendo l'ordine editoriale.
                    var seen = Set<String>()
                    articles = valid.filter { seen.insert($0.id).inserted }
                    errorMessage = nil
                    await loadItalianTitles()
                    return
                }
            } catch {
                // Prova la seconda sorgente, senza interrompere il player radio.
                continue
            }
        }

        if articles.isEmpty {
            errorMessage = "Știrile nu sunt disponibile acum. Încearcă din nou."
        }
    }
}

import Foundation
import SwiftUI

/// Solo i brani pubblici, approvati e autorizzati all'ascolto dall'API RDI.
struct RDIAITrack: Decodable, Identifiable, Hashable {
    let id: String
    let title: String
    let artist: String

    var audioURL: URL? {
        guard id.range(of: "^[0-9a-f]{32}$", options: .regularExpression) != nil else {
            return nil
        }
        return URL(string: "https://radioromanii.duckdns.org/api/ai-music/spotlight/\(id)/audio")
    }
}

private struct RDIAIPlaylistResponse: Decodable {
    let tracks: [RDIAITrack]
}

@MainActor
final class RDIAIMusicStore: ObservableObject {
    @Published private(set) var tracks: [RDIAITrack] = []
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?

    private let playlistURL = URL(
        string: "https://radioromanii.duckdns.org/api/ai-music/spotlight/playlist"
    )!

    func refresh() async {
        guard !isLoading else { return }
        isLoading = true
        defer { isLoading = false }

        do {
            var request = URLRequest(url: playlistURL)
            request.cachePolicy = .reloadIgnoringLocalCacheData
            request.timeoutInterval = 18

            let (data, response) = try await URLSession.shared.data(for: request)
            guard let response = response as? HTTPURLResponse,
                  (200...299).contains(response.statusCode) else {
                throw URLError(.badServerResponse)
            }

            let payload = try JSONDecoder().decode(RDIAIPlaylistResponse.self, from: data)
            var seen = Set<String>()
            tracks = payload.tracks.filter {
                !$0.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                    && $0.audioURL != nil
                    && seen.insert($0.id).inserted
            }
            errorMessage = tracks.isEmpty
                ? "Non ci sono ancora brani AI autorizzati all'ascolto."
                : nil
        } catch {
            if tracks.isEmpty {
                errorMessage = "Impossibile caricare AI Music. Riprova quando la connessione è disponibile."
            }
        }
    }
}

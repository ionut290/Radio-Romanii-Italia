import SwiftUI
import WebKit

@main
struct RadioRomaniiApp: App {
    var body: some Scene {
        WindowGroup { RadioWebView().ignoresSafeArea() }
    }
}

struct RadioWebView: UIViewRepresentable {
    private let url = URL(string: "https://radioromanii.duckdns.org/")!

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.load(URLRequest(url: url, cachePolicy: .reloadRevalidatingCacheData))
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}
}

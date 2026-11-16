import SwiftUI

@main
struct RadioRomaniiItaliaApp: App {
    @StateObject private var radio = RadioPlayer()

    var body: some Scene {
        WindowGroup {
            RadioHomeView()
                .environmentObject(radio)
        }
    }
}

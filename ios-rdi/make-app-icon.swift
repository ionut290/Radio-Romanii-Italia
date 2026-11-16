import AppKit
import Foundation

let sourcePath = CommandLine.arguments[1]
let destinationPath = CommandLine.arguments[2]
guard let source = NSImage(contentsOfFile: sourcePath),
      source.size.width > 0, source.size.height > 0 else {
    fatalError("Impossibile leggere il logo RDI")
}

let size = 1024
guard let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size,
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
    isPlanar: false, colorSpaceName: .deviceRGB,
    bytesPerRow: 0, bitsPerPixel: 0
), let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
    fatalError("Impossibile generare icona")
}

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = context
context.imageInterpolation = .high
NSColor(calibratedRed: 0.065, green: 0.11, blue: 0.19, alpha: 1).setFill()
NSRect(x: 0, y: 0, width: size, height: size).fill()

let maxSide: CGFloat = 850
let ratio = min(maxSide / source.size.width, maxSide / source.size.height)
let w = source.size.width * ratio
let h = source.size.height * ratio
source.draw(in: NSRect(x: (CGFloat(size) - w) / 2,
                       y: (CGFloat(size) - h) / 2,
                       width: w, height: h),
            from: NSRect(origin: .zero, size: source.size),
            operation: .sourceOver, fraction: 1)
context.flushGraphics()
NSGraphicsContext.restoreGraphicsState()

guard let png = bitmap.representation(using: .png, properties: [:]) else {
    fatalError("Impossibile esportare PNG")
}
try png.write(to: URL(fileURLWithPath: destinationPath), options: .atomic)
print("Icona RDI 1024x1024 generata")

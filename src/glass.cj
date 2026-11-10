package xin_xuan_glass_probe

import cui.*
import std.fs.{File, Path}

class Backdrop <: Resource {
    let original: Array<UInt8>
    let frosted: Array<UInt8>
    var clearTexture: ?Texture = None
    var blurTexture: ?Texture = None
    var viewport = Rect(0.0, 0.0, 1100.0, 780.0)
    var closed = false

    init(assetRoot!: String = "assets") {
        diagnosticStage("G10_BEFORE_BACKGROUND_READ")
        original = File.readFrom(Path(assetRoot).join(Path("rain-window.bmp")))
        diagnosticStage("G15_BEFORE_BLUR")
        frosted = blurBmp(original, 32)
        diagnosticStage("G20_BLUR_FINISHED")
        println("BLUR_READY source=${original.size} bytes radius=32 passes=3")
    }

    func ensure(renderer: Renderer): Unit {
        if (clearTexture.isNone()) {
            diagnosticStage("G50_BEFORE_SOURCE_DECODE")
            let source = Surface.loadBytes(original, typeHint: "BMP")
            diagnosticStage("G55_BEFORE_SOURCE_TEXTURE")
            try { clearTexture = Some(renderer.textureFromSurface(source)) } finally { source.close() }
            diagnosticStage("G60_BEFORE_BLURRED_DECODE")
            let blurred = Surface.loadBytes(frosted, typeHint: "BMP")
            diagnosticStage("G65_BEFORE_BLURRED_TEXTURE")
            try { blurTexture = Some(renderer.textureFromSurface(blurred)) } finally { blurred.close() }
            diagnosticStage("G70_TEXTURES_READY")
            println("TEXTURES_READY")
        }
    }

    public func close(): Unit {
        if (closed) { return }
        match (clearTexture) { case Some(t) => t.close(); case None => () }
        match (blurTexture) { case Some(t) => t.close(); case None => () }
        closed = true
    }

    public func isClosed(): Bool { closed }
}

class GlassLayer <: Widget {
    let backdrop: Backdrop
    let paintsBackground: Bool
    let frosted: Bool
    var frame = Rect.zero()

    init(backdrop: Backdrop, background!: Bool = false, frosted!: Bool = true) {
        this.backdrop = backdrop
        this.paintsBackground = background
        this.frosted = frosted
        emit(this)
    }

    public func measure(_: UiContext, available: Size): Size { available }
    public func layout(_: UiContext, rect: Rect): Unit { frame = rect }
    public func isFlexible(): Bool { true }
    public func handle(_: UiContext, _: UiEvent): Bool { false }

    public func draw(ctx: UiContext): Unit {
        backdrop.ensure(ctx.renderer)
        if (paintsBackground) {
            backdrop.viewport = frame
            ctx.renderer.texture(backdrop.clearTexture.getOrThrow(), frame)
            return
        }
        let texture = if (frosted) { backdrop.blurTexture.getOrThrow() } else { backdrop.clearTexture.getOrThrow() }
        let viewport = backdrop.viewport
        let sx = max(0.0, (frame.x - viewport.x) / viewport.w * texture.width)
        let sy = max(0.0, (frame.y - viewport.y) / viewport.h * texture.height)
        let source = Rect(sx, sy, min(texture.width - sx, frame.w / viewport.w * texture.width),
            min(texture.height - sy, frame.h / viewport.h * texture.height))
        ctx.renderer.textureStyled(texture, frame, source: Some(source), style: TextureStyle(radius: 22.0))
        ctx.renderer.fillRoundedRect(frame, 22.0, Color.rgba(244, 255, 251, 102))
        ctx.renderer.strokeRoundedRect(frame.inset(0.5), 22.0, Pen(width: 1.0, color: Color.rgba(255, 255, 255, 220)))
    }
}

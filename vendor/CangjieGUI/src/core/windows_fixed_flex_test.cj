package cui.core

import sdl.{Rect, Size}

@Test
func windowsFixedHeightDoesNotReserveFlexibleSpace(): Unit {
    let fixed = LayoutProbe()
    let rest = LayoutProbe()
    let view = VStack {
        emit(fixed); fixed.flex().height(40.0)
        emit(rest); rest.flex()
    }.spacing(0.0)
    view.layout(testContext(), Rect(0.0, 0.0, 300.0, 200.0))
    @Expect(rest.rect.y, Float32(40.0))
    @Expect(rest.rect.h, Float32(160.0))
}

@Test
func windowsFixedWidthDoesNotReserveFlexibleSpace(): Unit {
    let fixed = LayoutProbe()
    let rest = LayoutProbe()
    let view = HStack {
        emit(fixed); fixed.flex().width(60.0)
        emit(rest); rest.flex()
    }.spacing(0.0)
    view.layout(testContext(), Rect(0.0, 0.0, 300.0, 200.0))
    @Expect(rest.rect.x, Float32(60.0))
    @Expect(rest.rect.w, Float32(240.0))
}

@Test
func windowsExplicitFlexStillSharesUnpinnedAxis(): Unit {
    let first = LayoutProbe()
    let second = LayoutProbe()
    let view = VStack {
        emit(first); first.flex(1.0).width(60.0)
        emit(second); second.flex(3.0)
    }.spacing(0.0)
    view.layout(testContext(), Rect(0.0, 0.0, 300.0, 200.0))
    @Expect(first.rect.h, Float32(50.0))
    @Expect(second.rect.h, Float32(150.0))
}

package xin_xuan_glass_probe

import cui.*
import std.fs.{Directory, exists, remove}
import xin_xuan_glass_probe.application.CatalogController
import xin_xuan_glass_probe.storage.LocalStore

private func uiRoot(): String {
    if (!exists("target/ui-tests")) { Directory.create("target/ui-tests", recursive: true) }
    Directory.createTemp("target/ui-tests").toString()
}

@Test
func nativeControlsEditBudgetAndDeleteOnlyAfterConfirmation(): Unit {
    let root = uiRoot()
    configureShoppingFonts()
    let window = SdlWindow(WindowSpec("Control checks", 760, 420), hidden: true)
    let materials = Backdrop()
    let host = WidgetTestHost(renderer: window.renderer, theme: shoppingTheme())
    try {
        let vm = CatalogViewModel(CatalogController(LocalStore(root), "assets"))
        let build: () -> Unit = {=> shoppingView(vm, materials)}
        let rect = Rect(0.0, 0.0, 760.0, 420.0)
        let _ = host.frame(rect, body: build)
        window.renderer.captureBmp("target/catalog-list.bmp")
        @Expect(host.context.performSemanticsAction("budget", SemanticsAction.SetValue("600")))
        let _ = host.frame(rect, body: build)
        @Expect(vm.model.state.budget, Some(600))
        @Expect(host.context.performSemanticsAction("delete-0", SemanticsAction.Activate))
        let _ = host.frame(rect, body: build)
        @Expect(host.context.performSemanticsAction("cancel-delete", SemanticsAction.Activate))
        let _ = host.frame(rect, body: build)
        @Expect(vm.model.state.products.size, 5)
        @Expect(host.context.performSemanticsAction("delete-0", SemanticsAction.Activate))
        let _ = host.frame(rect, body: build)
        @Expect(host.context.performSemanticsAction("confirm-delete", SemanticsAction.Activate))
        let _ = host.frame(rect, body: build)
        @Expect(vm.view.value.rows.size, 4)
        @Expect(host.context.performSemanticsAction("name-1", SemanticsAction.SetValue("改名台灯")))
        let _ = host.frame(rect, body: build)
        @Expect(vm.model.state.products[0].name, "改名台灯")
        vm.change({=> vm.model.editPrice(vm.model.keys[0], "无效")})
        let _ = host.frame(rect, events: [UiEvent.MouseWheel(0.0, -1000.0, 600.0, 300.0)], body: build)
        var retryVisible = false
        for (node in host.context.semanticsSnapshot()) {
            if (node.id == "retry-save") {
                retryVisible = true
                @Expect(node.bounds.y >= 0.0 && node.bounds.y + node.bounds.h <= rect.h)
            }
        }
        @Expect(retryVisible)
    } finally { host.reset(); materials.close(); window.close(); remove(root, recursive: true) }
}

@Test
func nativeRatingControlsDisableNextAndResultsNeverExposeScores(): Unit {
    let root = uiRoot()
    configureShoppingFonts()
    let window = SdlWindow(WindowSpec("Rating checks", 640, 400), hidden: true)
    let materials = Backdrop()
    let host = WidgetTestHost(renderer: window.renderer, displayScale: 1.5, theme: shoppingTheme())
    try {
        let vm = CatalogViewModel(CatalogController(LocalStore(root), "assets"))
        let build: () -> Unit = {=> shoppingView(vm, materials)}
        let rect = Rect(0.0, 0.0, 640.0, 400.0)
        let _ = host.frame(rect, body: build)
        @Expect(host.context.performSemanticsAction("budget", SemanticsAction.SetValue("600")))
        let _ = host.frame(rect, body: build)
        @Expect(host.context.performSemanticsAction("nav-rate", SemanticsAction.Activate))
        let _ = host.frame(rect, body: build)
        window.renderer.captureBmp("target/catalog-rating.bmp")
        @Expect(!host.context.performSemanticsAction("next-item", SemanticsAction.Activate))
        @Expect(host.context.performSemanticsAction("rating-3", SemanticsAction.Activate))
        let _ = host.frame(rect, body: build)
        @Expect(host.context.performSemanticsAction("next-item", SemanticsAction.Activate))
        let _ = host.frame(rect, body: build)
        @Expect(vm.view.value.ratingIndex, 1)
        @Expect(host.context.performSemanticsAction("previous-item", SemanticsAction.Activate))
        let _ = host.frame(rect, body: build)
        @Expect(vm.view.value.rows[0].item.rating, Some(3))
        vm.change({=>
            for (i in 0..5) { vm.model.setRating(i, 10000) }
            vm.model.calculate()
        })
        let _ = host.frame(rect, body: build)
        window.renderer.captureBmp("target/catalog-results.bmp")
        @Expect(vm.view.value.plans.size, 3)
        var bestSeen = false
        for (node in host.context.semanticsSnapshot()) {
            let text = node.properties.label
            @Expect(!text.contains("10000") && !text.contains("总分"))
            if (text == "最佳方案") { bestSeen = true }
        }
        @Expect(bestSeen)
    } finally { host.reset(); materials.close(); window.close(); remove(root, recursive: true) }
}

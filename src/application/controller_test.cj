package xin_xuan_glass_probe.application

import std.fs.{Directory, exists, remove}
import xin_xuan_glass_probe.shopping.Product
import xin_xuan_glass_probe.storage.{LocalStore, ShoppingState, SnapshotWriter, NativeSnapshotWriter}

private func fixtureRoot(): String {
    if (!exists("target/catalog-tests")) { Directory.create("target/catalog-tests", recursive: true) }
    Directory.createTemp("target/catalog-tests").toString()
}

@Test
func catalogFirstLaunchShowsFiveUnratedExamplesAndEmptyBudget(): Unit {
    let root = fixtureRoot()
    try {
        let catalog = CatalogController(LocalStore(root), "assets")
        @Expect(catalog.state.products.size, 5)
        @Expect(catalog.budgetText, "")
        @Expect(catalog.state.budget, None)
        @Expect(catalog.state.firstUnrated(), Some(0))
        @Expect(!catalog.ratingOpen)
        @Expect(!catalog.needsCloseConfirmation())
        let reopened = CatalogController(LocalStore(root), "assets")
        @Expect(reopened.state.products.size, 5)
        @Expect(!reopened.ratingOpen)
    } finally { remove(root, recursive: true) }
}

@Test
func catalogExistingEmptyCatalogDoesNotReloadSamples(): Unit {
    let root = fixtureRoot()
    try {
        let _ = LocalStore(root).save(ShoppingState(None, []))
        let catalog = CatalogController(LocalStore(root), "assets")
        @Expect(catalog.state.products.size, 0)
    } finally { remove(root, recursive: true) }
}

@Test
func catalogInvalidDraftRemainsVisibleAndBlocksComputeAndSafeClose(): Unit {
    let root = fixtureRoot()
    try {
        let catalog = CatalogController(LocalStore(root), "assets")
        catalog.editBudget("600")
        let key = catalog.keys[0]
        catalog.editPrice(key, "12.5")
        @Expect(catalog.priceText(key), "12.5")
        @Expect(catalog.needsCloseConfirmation())
        catalog.beginRating()
        @Expect(!catalog.ratingOpen)
        @Expect(!catalog.notice.isEmpty())
        @Expect(!catalog.retryBeforeClose())
        catalog.editPrice(key, "125")
        @Expect(!catalog.needsCloseConfirmation())
        @Expect(catalog.state.products[0].price, 125)
    } finally { remove(root, recursive: true) }
}

@Test
func catalogEditingPreservesRatingAndRecalculatesResults(): Unit {
    let root = fixtureRoot()
    try {
        let catalog = CatalogController(LocalStore(root), "assets")
        catalog.editBudget("600")
        for (i in 0..5) { catalog.setRating(i, 3) }
        catalog.calculate()
        @Expect(catalog.showResults)
        let key = catalog.keys[0]
        catalog.editName(key, "新耳机")
        catalog.editPrice(key, "1")
        @Expect(catalog.state.products[0].rating, Some(3))
        @Expect(catalog.state.products[0].name, "新耳机")
        @Expect(catalog.plans.size, 3)
        @Expect(catalog.plans[0].totalPrice <= 600)
    } finally { remove(root, recursive: true) }
}

@Test
func catalogDeleteNeedsConfirmationAndKeepsRemainingRowKeysStable(): Unit {
    let root = fixtureRoot()
    try {
        let catalog = CatalogController(LocalStore(root), "assets")
        let first = catalog.keys[0]
        let second = catalog.keys[1]
        catalog.requestDelete(first)
        catalog.cancelDelete()
        @Expect(catalog.state.products.size, 5)
        catalog.requestDelete(first)
        catalog.confirmDelete()
        @Expect(catalog.state.products.size, 4)
        @Expect(catalog.keys[0], second)
        catalog.editName(second, "改名台灯")
        @Expect(catalog.state.products[0].name, "改名台灯")
    } finally { remove(root, recursive: true) }
}

@Test
func catalogRatingRequiresChoicePreservesPreviousAndEndsWithThreePlans(): Unit {
    let root = fixtureRoot()
    try {
        let catalog = CatalogController(LocalStore(root), "assets")
        catalog.editBudget("600")
        catalog.beginRating()
        @Expect(catalog.ratingOpen)
        @Expect(catalog.ratingIndex, 0)
        catalog.nextRating()
        @Expect(catalog.ratingIndex, 0)
        catalog.setRating(0, 3)
        catalog.nextRating()
        @Expect(catalog.ratingIndex, 1)
        catalog.previousRating()
        @Expect(catalog.state.products[0].rating, Some(3))
        for (i in 0..5) { catalog.setRating(i, 3) }
        for (_ in 0..5) { catalog.nextRating() }
        @Expect(!catalog.ratingOpen)
        @Expect(catalog.showResults)
        @Expect(catalog.plans.size, 3)
        let restored = CatalogController(LocalStore(root), "assets")
        @Expect(!restored.ratingOpen)
        restored.beginRating()
        @Expect(restored.showResults)
    } finally { remove(root, recursive: true) }
}

private class BlockPublication <: SnapshotWriter {
    let native = NativeSnapshotWriter()
    var blocked = false
    public func writeNew(path: String, data: Array<UInt8>): Unit { native.writeNew(path, data) }
    public func publish(source: String, destination: String): Unit {
        if (blocked) { throw IllegalArgumentException("模拟保存失败") }
        native.publish(source, destination)
    }
}

@Test
func catalogRetryBeforeCloseOnlyApprovesAfterSuccessfulSave(): Unit {
    let root = fixtureRoot()
    try {
        let writer = BlockPublication()
        let catalog = CatalogController(LocalStore(root, writer: writer), "assets")
        writer.blocked = true
        catalog.editBudget("500")
        @Expect(catalog.needsCloseConfirmation())
        @Expect(!catalog.retryBeforeClose())
        @Expect(catalog.state.budget, Some(500))
        writer.blocked = false
        @Expect(catalog.retryBeforeClose())
        @Expect(!catalog.needsCloseConfirmation())
    } finally { remove(root, recursive: true) }
}

@Test
func catalogEditingAfterViewingResultsDoesNotInterruptTyping(): Unit {
    let root = fixtureRoot()
    try {
        let catalog = CatalogController(LocalStore(root), "assets")
        catalog.editBudget("600")
        for (i in 0..5) { catalog.setRating(i, 3) }
        catalog.calculate()
        catalog.showCatalog()
        catalog.editName(catalog.keys[0], "改名")
        @Expect(!catalog.showResults)
        @Expect(catalog.plans.size, 3)
    } finally { remove(root, recursive: true) }
}

package xin_xuan_glass_probe.storage

import std.fs.{Directory, File, Path, exists, remove}
import xin_xuan_glass_probe.shopping.Product

private func freshRoot(): String {
    if (!exists("target/storage-tests")) { Directory.create("target/storage-tests", recursive: true) }
    Directory.createTemp("target/storage-tests").toString()
}

private func sampleState(image!: String = "assets/headphones.jpg"): ShoppingState {
    ShoppingState(Some(600), [Product("耳机,\"轻盈\"\n版", 299, Some(3), image), Product("耳机", 169, None, image)])
}

@Test
func storageRoundTripsBudgetChineseAndUnratedProducts(): Unit {
    let root = freshRoot()
    try {
        let saved = LocalStore(root).save(sampleState())
        let restored = LocalStore(root).load()
        @Expect(restored.warning.isEmpty())
        @Expect(restored.state.isSome())
        let state = restored.state.getOrThrow()
        @Expect(state.budget, Some(600))
        @Expect(state.products.size, 2)
        @Expect(state.products[0].name, "耳机,\"轻盈\"\n版")
        @Expect(state.products[1].rating, None)
        @Expect(exists(state.products[0].imagePath))
        @Expect(state.firstUnrated(), Some(1))
        @Expect(saved.products[0].imagePath, state.products[0].imagePath)
    } finally { remove(root, recursive: true) }
}

@Test
func storageImagesSurviveMovingOriginalAndDoNotDuplicateOnRatingSave(): Unit {
    let root = freshRoot()
    let original = Path(root).join(Path("original.jpg")).toString()
    try {
        File.writeTo(original, File.readFrom("assets/headphones.jpg"))
        let store = LocalStore(Path(root).join(Path("app-data")).toString())
        let saved = store.save(sampleState(image: original))
        remove(original)
        let loaded = store.load().state.getOrThrow()
        @Expect(exists(loaded.products[0].imagePath))
        @Expect(loaded.products[0].imagePath, loaded.products[1].imagePath)
        let again = store.save(loaded)
        @Expect(again.products[0].imagePath, saved.products[0].imagePath)
    } finally { remove(root, recursive: true) }
}

@Test
func storageEmptyStateAndInterruptedPendingFileAreSafe(): Unit {
    let root = freshRoot()
    try {
        let store = LocalStore(root)
        @Expect(store.load().state.isNone())
        let _ = store.save(ShoppingState(None, []))
        File.writeTo(Path(root).join(Path("snapshots/999.pending")), "incomplete".toArray())
        let loaded = store.load()
        @Expect(loaded.state.getOrThrow().budget, None)
        @Expect(loaded.state.getOrThrow().products.size, 0)
        @Expect(loaded.warning.isEmpty())
    } finally { remove(root, recursive: true) }
}

@Test
func storageCorruptNewestFallsBackWithoutOverwritingEvidence(): Unit {
    let root = freshRoot()
    try {
        let store = LocalStore(root)
        let _ = store.save(ShoppingState(Some(100), []))
        let _ = store.save(ShoppingState(Some(200), []))
        let file = Path(root).join(Path("snapshots/2.snapshot")).toString()
        File.writeTo(file, "damaged".toArray())
        let result = store.load()
        @Expect(result.state.getOrThrow().budget, Some(100))
        @Expect(!result.warning.isEmpty())
        @Expect(String.fromUtf8(File.readFrom(file)), "damaged")
    } finally { remove(root, recursive: true) }
}

@Test
func storageAllCorruptDoesNotPretendToRestoreEmptyState(): Unit {
    let root = freshRoot()
    try {
        let store = LocalStore(root)
        let _ = store.save(ShoppingState(None, []))
        File.writeTo(Path(root).join(Path("snapshots/1.snapshot")), "damaged".toArray())
        let result = store.load()
        @Expect(result.state.isNone())
        @Expect(!result.warning.isEmpty())
    } finally { remove(root, recursive: true) }
}

private class FailingWriter <: SnapshotWriter {
    let native = NativeSnapshotWriter()
    var failWrite = false
    var failPublish = false
    var writes: Int64 = 0
    var failAtWrite: Int64 = 0
    public func writeNew(path: String, data: Array<UInt8>): Unit {
        writes += 1
        if (failWrite || writes == failAtWrite) { throw IllegalArgumentException("磁盘写入失败") }
        native.writeNew(path, data)
    }
    public func publish(source: String, destination: String): Unit {
        if (failPublish) { throw IllegalArgumentException("发布失败") }
        native.publish(source, destination)
    }
}

@Test
func storageFailedPublishKeepsPreviousSaveAndInMemoryChangesThenRetries(): Unit {
    let root = freshRoot()
    try {
        let writer = FailingWriter()
        let store = LocalStore(root, writer: writer)
        let _ = store.save(ShoppingState(Some(100), []))
        let session = ShoppingSession(store)
        writer.failPublish = true
        session.update(ShoppingState(Some(200), []))
        @Expect(session.state.budget, Some(200))
        @Expect(session.unsaved)
        @Expect(session.saveMessage.contains("尚未保存"))
        @Expect(store.load().state.getOrThrow().budget, Some(100))
        writer.failPublish = false
        session.retrySave()
        @Expect(!session.unsaved)
        @Expect(store.load().state.getOrThrow().budget, Some(200))
    } finally { remove(root, recursive: true) }
}

@Test
func storageCopyFailureDoesNotCommitPartialCatalog(): Unit {
    let root = freshRoot()
    try {
        let writer = FailingWriter()
        let store = LocalStore(root, writer: writer)
        let _ = store.save(ShoppingState(Some(100), []))
        let session = ShoppingSession(store)
        writer.writes = 0
        writer.failAtWrite = 2 // First image was copied; snapshot write then fails.
        session.update(sampleState())
        @Expect(session.unsaved)
        @Expect(session.state.products.size, 2)
        @Expect(store.load().state.getOrThrow().products.size, 0)
        @Expect(Directory.isEmpty(Path(root).join(Path("images"))))
    } finally { remove(root, recursive: true) }
}

@Test
func storageCodecRejectsCorruptionTruncationAndInvalidState(): Unit {
    let good = encodeState(ShoppingState(Some(1000), [Product("商品", 1, Some(10000), "images/batch/a.jpg")]))
    let decoded = decodeState(good)
    @Expect(decoded.products[0].rating, Some(10000))
    let bad = good.clone()
    bad[10] = bad[10] ^ UInt8(1)
    for (data in [bad, good[0..good.size - 1], "unknown version".toArray()]) {
        var rejected = false
        try { let _ = decodeState(data) } catch (_: Exception) { rejected = true }
        @Expect(rejected)
    }
    for (image in ["../outside.jpg", "/outside.jpg", "images/../../outside.jpg"]) {
        var rejected = false
        try { let _ = encodeState(ShoppingState(None, [Product("商品", 1, None, image)])) }
        catch (_: Exception) { rejected = true }
        @Expect(rejected)
    }
}

@Test
func storageMissingOwnedImageWarnsWithoutDroppingProductsOrRatings(): Unit {
    let root = freshRoot()
    try {
        let store = LocalStore(root)
        let saved = store.save(sampleState())
        remove(saved.products[0].imagePath)
        let restored = store.load()
        @Expect(restored.state.getOrThrow().products.size, 2)
        @Expect(restored.state.getOrThrow().products[0].rating, Some(3))
        @Expect(!restored.warning.isEmpty())
    } finally { remove(root, recursive: true) }
}

@Test
func storageBlockedRootDoesNotLookLikeFirstLaunch(): Unit {
    let root = freshRoot()
    try {
        let blocked = Path(root).join(Path("blocked")).toString()
        File.writeTo(blocked, "not a directory".toArray())
        let result = LocalStore(blocked).load()
        @Expect(result.state.isNone())
        @Expect(!result.warning.isEmpty())
    } finally { remove(root, recursive: true) }
}

@Test
func storageSessionContinuesRatingAfterFailureAndRestartPreservesProgress(): Unit {
    let root = freshRoot()
    try {
        let writer = FailingWriter()
        let store = LocalStore(root, writer: writer)
        let saved = store.save(sampleState())
        let session = ShoppingSession(store)
        let items = saved.products.clone()
        items[1] = Product(items[1].name, items[1].price, Some(10000), items[1].imagePath)
        writer.failPublish = true
        session.update(ShoppingState(Some(500), items))
        @Expect(session.unsaved)
        @Expect(session.state.products[1].rating, Some(10000))
        @Expect(session.state.firstUnrated().isNone())
        writer.failPublish = false
        session.retrySave()
        let restarted = ShoppingSession(store)
        @Expect(!restarted.unsaved)
        @Expect(restarted.state.budget, Some(500))
        @Expect(restarted.state.products[1].rating, Some(10000))
    } finally { remove(root, recursive: true) }
}

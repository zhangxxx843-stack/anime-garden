package xin_xuan_glass_probe.storage

import std.collection.{ArrayList, HashMap}
import std.fs.{Directory, File, FileInfo, Path, exists, remove, rename}
import xin_xuan_glass_probe.shopping.Product
import xin_xuan_glass_probe.importing.checkLocalProductImage

/** Publication never overwrites an existing snapshot. */
public interface SnapshotWriter {
    func writeNew(path: String, data: Array<UInt8>): Unit
    func publish(source: String, destination: String): Unit
}

public class NativeSnapshotWriter <: SnapshotWriter {
    public func writeNew(path: String, data: Array<UInt8>): Unit {
        if (exists(path)) { throw IllegalArgumentException("新存档位置已存在，未覆盖原文件。") }
        File.writeTo(path, data)
    }
    public func publish(source: String, destination: String): Unit {
        rename(source, to: destination)
    }
}

private func ensureDirectory(path: String): Unit {
    if (!exists(path)) { Directory.create(path, recursive: true) }
    if (!FileInfo(path).isDirectory()) { throw IllegalArgumentException("数据目录不是文件夹。") }
}

private func generation(name: String): ?Int64 {
    if (!name.endsWith(".snapshot")) { return None }
    let digits = name[0..name.size - 9]
    if (digits.isEmpty()) { return None }
    var value: Int64 = 0
    for (byte in digits.toArray()) {
        if (byte < 48 || byte > 57 || value > (Int64.Max - 9) / 10) { return None }
        value = value * 10 + Int64(byte - 48)
    }
    if (value > 0) { Some(value) } else { None }
}

public class LocalStore {
    private let root: String
    private let writer: SnapshotWriter
    public init(root: String, writer!: SnapshotWriter = NativeSnapshotWriter()) {
        if (root.isEmpty()) { throw IllegalArgumentException("未指定本地数据目录。") }
        this.root = Path(root).normalize().toString(); this.writer = writer
    }
    private func at(relative: String): String { Path(root).join(Path(relative)).normalize().toString() }

    private func records(): ArrayList<(Int64, String)> {
        let result = ArrayList<(Int64, String)>()
        if (!exists(at("snapshots"))) { return result }
        for (info in Directory.readFrom(at("snapshots"))) {
            if (let Some(value) <- generation(info.name)) { result.add((value, info.path.toString())) }
        }
        result
    }

    public func save(state: ShoppingState): ShoppingState {
        validateState(state)
        ensureDirectory(root); ensureDirectory(at("images")); ensureDirectory(at("snapshots"))
        var latest: Int64 = 0
        for ((value, _) in records()) { latest = max(latest, value) }
        if (latest == Int64.Max) { throw IllegalArgumentException("存档版本号已超出范围。") }
        let attempt = Directory.createTemp(at("images"))
        var committed = false
        try {
            let stored = ArrayList<Product>()
            let resolved = ArrayList<Product>()
            let images = HashMap<String, String>()
            for (index in 0..state.products.size) {
                let item = state.products[index]
                var key = ""
                if (!item.imagePath.isEmpty()) {
                    let source = Path(item.imagePath).normalize().toString()
                    if (let Some(problem) <- checkLocalProductImage(source)) { throw IllegalArgumentException(problem) }
                    match (images.get(source)) {
                        case Some(existing) => key = existing
                        case None =>
                            let slashSource = source.replace("\\", "/")
                            let prefix = root.replace("\\", "/") + "/"
                            if (slashSource.startsWith(prefix + "images/")) {
                                key = slashSource[prefix.size..slashSource.size]
                                validateStoredImage(key)
                            } else {
                                let filename = "${index}-${Path(source).fileName}"
                                key = "images/${attempt.fileName}/${filename}"
                                writer.writeNew(at(key), File.readFrom(source))
                                if (let Some(problem) <- checkLocalProductImage(at(key))) { throw IllegalArgumentException(problem) }
                            }
                            images.add(source, key)
                    }
                }
                stored.add(Product(item.name, item.price, item.rating, key))
                resolved.add(Product(item.name, item.price, item.rating, if (key.isEmpty()) { "" } else { at(key) }))
            }
            let pending = attempt.join(Path("state.pending")).toString()
            writer.writeNew(pending, encodeState(ShoppingState(state.budget, stored.toArray())))
            writer.publish(pending, at("snapshots/${latest + 1}.snapshot"))
            committed = true
            ShoppingState(state.budget, resolved.toArray())
        } finally {
            // Only this attempt's new files may be removed; previous snapshots/images remain untouched.
            try {
                if (!committed || Directory.isEmpty(attempt)) { remove(attempt, recursive: true) }
            } catch (_: Exception) { () }
        }
    }

    public func load(): RestoreResult {
        try {
            if (exists(root) && !FileInfo(root).isDirectory()) {
                throw IllegalArgumentException("数据位置不是文件夹。")
            }
            let candidates = records()
            var damaged = false
            while (!candidates.isEmpty()) {
                var best: Int64 = 0
                for (i in 1..candidates.size) { if (candidates[i][0] > candidates[best][0]) { best = i } }
                let (_, path) = candidates.remove(at: best)
                let state = try { decodeState(File.readFrom(path)) }
                catch (_: Exception) { damaged = true; continue }
                let products = ArrayList<Product>()
                var missingImage = false
                for (item in state.products) {
                    let image = if (item.imagePath.isEmpty()) { "" } else { at(item.imagePath) }
                    if (!image.isEmpty() && checkLocalProductImage(image).isSome()) { missingImage = true }
                    products.add(Product(item.name, item.price, item.rating, image))
                }
                var warning = if (damaged) { "最新存档损坏，已恢复上一份有效数据，最近修改可能未恢复。" } else { "" }
                if (missingImage) { warning += "部分本地图片缺失或损坏，商品与评分已保留，请补图。" }
                return RestoreResult(Some(ShoppingState(state.budget, products.toArray())), warning)
            }
            RestoreResult(None, if (damaged) { "本地存档损坏，未恢复数据；原文件已保留，请勿覆盖。" } else { "" })
        } catch (_: Exception) { RestoreResult(None, "无法读取本地数据，原文件已保留，请检查存储位置和权限。") }
    }
}

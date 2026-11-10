package xin_xuan_glass_probe.storage

import xin_xuan_glass_probe.shopping.Product

public struct ShoppingState {
    public let budget: ?Int64
    public let products: Array<Product>
    public init(budget: ?Int64, products: Array<Product>) {
        this.budget = budget; this.products = products.clone()
    }
    public func firstUnrated(): ?Int64 {
        for (i in 0..products.size) { if (products[i].rating.isNone()) { return Some(i) } }
        None
    }
}

public struct RestoreResult {
    public let state: ?ShoppingState
    public let warning: String
    public init(state: ?ShoppingState, warning: String) { this.state = state; this.warning = warning }
}

internal func validateState(state: ShoppingState, storedPaths!: Bool = false): Unit {
    if (let Some(budget) <- state.budget) {
        if (budget < 1 || budget > 1000) { throw IllegalArgumentException("预算须为 1 到 1000 的整数。") }
    }
    for (item in state.products) {
        if (item.name.trimAscii().isEmpty() || item.name.contains("\u{0}")) {
            throw IllegalArgumentException("商品名称为空或包含空字符。")
        }
        if (item.price < 1 || item.price > 1000) { throw IllegalArgumentException("商品价格无效。") }
        if (let Some(rating) <- item.rating) {
            if (rating != -1 && rating != 1 && rating != 2 && rating != 3 && rating != 10000) {
                throw IllegalArgumentException("喜欢程度无效。")
            }
        }
        if (storedPaths && !item.imagePath.isEmpty()) { validateStoredImage(item.imagePath) }
    }
}

internal func validateStoredImage(path: String): Unit {
    let normalized = path.replace("\\", "/")
    if (!normalized.startsWith("images/") || normalized.contains(":") || normalized.contains("\u{0}")) {
        throw IllegalArgumentException("存档图片路径无效。")
    }
    for (part in normalized.split("/")) {
        if (part.isEmpty() || part == "." || part == "..") { throw IllegalArgumentException("存档图片路径越界。") }
    }
}

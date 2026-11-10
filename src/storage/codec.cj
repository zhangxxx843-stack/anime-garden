package xin_xuan_glass_probe.storage

import std.collection.ArrayList
import xin_xuan_glass_probe.shopping.Product

private let MAGIC = "XXSHOP01"

// Adler-32 detects accidental file corruption; it is not an authenticity check.
private func checksum(data: Array<UInt8>): Int64 {
    var a: Int64 = 1
    var b: Int64 = 0
    for (byte in data) { a = (a + Int64(byte)) % 65521; b = (b + a) % 65521 }
    (b << 16) | a
}

private func writeU32(out: ArrayList<UInt8>, value: Int64): Unit {
    if (value < 0 || value > 4294967295) { throw IllegalArgumentException("存档字段过大。") }
    for (i in 0..4) { out.add(UInt8((value >> (i * 8)) & 255)) }
}

private func writeString(out: ArrayList<UInt8>, value: String): Unit {
    writeU32(out, value.size)
    for (byte in value.toArray()) { out.add(byte) }
}

private class StateReader {
    let data: Array<UInt8>
    var position: Int64 = 0
    init(data: Array<UInt8>) { this.data = data }
    func u32(): Int64 {
        if (position > data.size - 4) { throw IllegalArgumentException("存档被截断。") }
        var result: Int64 = 0
        for (i in 0..4) { result = result | (Int64(data[position + i]) << (i * 8)) }
        position += 4
        result
    }
    func text(): String {
        let count = u32()
        if (count > data.size - position) { throw IllegalArgumentException("存档字段长度错误。") }
        let result = String.fromUtf8(data[position..position + count])
        position += count
        result
    }
    func remaining(): Int64 { data.size - position }
}

internal func encodeState(state: ShoppingState): Array<UInt8> {
    validateState(state, storedPaths: true)
    let out = ArrayList<UInt8>()
    for (byte in MAGIC.toArray()) { out.add(byte) }
    writeU32(out, state.budget.getOrDefault({=> 0}))
    writeU32(out, state.products.size)
    for (item in state.products) {
        writeString(out, item.name)
        writeU32(out, item.price)
        writeU32(out, match (item.rating) { case Some(score) => score + 2; case None => 0 })
        writeString(out, item.imagePath)
    }
    writeU32(out, checksum(out.toArray()))
    out.toArray()
}

internal func decodeState(bytes: Array<UInt8>): ShoppingState {
    if (bytes.size < 20 || String.fromUtf8(bytes[0..8]) != MAGIC) { throw IllegalArgumentException("存档版本无法识别。") }
    let data = bytes[0..bytes.size - 4]
    let tail = StateReader(bytes[bytes.size - 4..bytes.size])
    if (tail.u32() != checksum(data)) { throw IllegalArgumentException("存档校验失败。") }
    let reader = StateReader(data)
    reader.position = 8
    let budgetValue = reader.u32()
    let budget: ?Int64 = if (budgetValue == 0) { None } else { Some(budgetValue) }
    let count = reader.u32()
    if (count > reader.remaining() / 16) { throw IllegalArgumentException("存档商品数量与内容不符。") }
    let products = ArrayList<Product>()
    for (_ in 0..count) {
        let name = reader.text()
        let price = reader.u32()
        let ratingCode = reader.u32()
        let rating: ?Int64 = if (ratingCode == 0) { None } else { Some(ratingCode - 2) }
        products.add(Product(name, price, rating, reader.text()))
    }
    if (reader.remaining() != 0) { throw IllegalArgumentException("存档含有无法识别的额外数据。") }
    let state = ShoppingState(budget, products.toArray())
    validateState(state, storedPaths: true)
    state
}

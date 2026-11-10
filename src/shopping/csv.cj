package xin_xuan_glass_probe.shopping

import std.collection.ArrayList
import std.fs.Path

public struct CsvIssue {
    public let line: Int64
    public let field: String
    public let message: String
    public init(line: Int64, field: String, message: String) {
        this.line = line; this.field = field; this.message = message
    }
}

/** Products remain empty on any error, preventing accidental partial imports. */
public struct CsvReport {
    public let products: Array<Product>
    public let issues: Array<CsvIssue>
    public let rowCount: Int64
    public let unratedCount: Int64
    public init(products: Array<Product>, issues: Array<CsvIssue>, rowCount: Int64, unratedCount: Int64) {
        this.products = products; this.issues = issues
        this.rowCount = rowCount; this.unratedCount = unratedCount
    }
}

private struct CsvRow {
    let line: Int64
    let cells: Array<String>
    init(line: Int64, cells: Array<String>) { this.line = line; this.cells = cells }
}

private func addRow(rows: ArrayList<CsvRow>, cells: ArrayList<String>, line: Int64): Unit {
    var nonempty = false
    for (cell in cells) { if (!cell.trimAscii().isEmpty()) { nonempty = true } }
    if (nonempty) { rows.add(CsvRow(line, cells.toArray())) }
}

// Parse bytes because CSV delimiters are ASCII; UTF-8 field bytes stay intact.
// Recoverable syntax errors are collected. Unclosed quoted text is ambiguous,
// so its remaining physical lines cannot safely be interpreted as separate rows.
private func parseRows(text: String, issues: ArrayList<CsvIssue>): Array<CsvRow> {
    let rows = ArrayList<CsvRow>()
    let cells = ArrayList<String>()
    let bytes = ArrayList<UInt8>()
    var quoted = false
    var closed = false
    var line: Int64 = 1
    var start: Int64 = 1
    var i: Int64 = if (text.startsWith("\u{FEFF}")) { 3 } else { 0 }
    while (i < text.size) {
        let ch = text[i]
        if (ch == 34) {
            if (quoted) {
                if (i + 1 < text.size && text[i + 1] == 34) { bytes.add(34); i += 1 }
                else { quoted = false; closed = true }
            } else if (bytes.isEmpty() && !closed) { quoted = true }
            else {
                issues.add(CsvIssue(line, "CSV 格式", "引号必须包住完整字段，字段内的引号须写成两个引号。"))
                bytes.add(ch)
            }
        } else if (ch == 10 || ch == 13) {
            if (ch == 13 && i + 1 < text.size && text[i + 1] == 10) { i += 1 }
            if (quoted) { bytes.add(10) }
            else {
                cells.add(String.fromUtf8(bytes.toArray()))
                addRow(rows, cells, start)
                cells.clear(); bytes.clear(); closed = false
            }
            line += 1
            if (!quoted) { start = line }
        } else if (ch == 44 && !quoted) {
            cells.add(String.fromUtf8(bytes.toArray()))
            bytes.clear(); closed = false
        } else {
            if (closed && ch != 32 && ch != 9) {
                issues.add(CsvIssue(line, "CSV 格式", "结束引号后只能是分隔符或换行。"))
                closed = false
            }
            if (!closed || quoted) { bytes.add(ch) }
        }
        i += 1
    }
    if (quoted) { issues.add(CsvIssue(start, "CSV 格式", "带引号的字段没有结束引号。")) }
    if (!bytes.isEmpty() || !cells.isEmpty() || closed) {
        cells.add(String.fromUtf8(bytes.toArray())); addRow(rows, cells, start)
    }
    rows.toArray()
}

private func parsePrice(value: String): ?Int64 {
    if (value.isEmpty()) { return None }
    var amount: Int64 = 0
    for (ch in value.toArray()) {
        if (ch < 48 || ch > 57) { return None }
        amount = amount * 10 + Int64(ch - 48)
        if (amount > 1000) { return None }
    }
    if (amount > 0) { Some(amount) } else { None }
}

private func parseRating(value: String): ?Int64 {
    match (value) {
        case "不喜欢" | "-1" => Some(-1)
        case "一般" | "1" => Some(1)
        case "较喜欢" | "2" => Some(2)
        case "喜欢" | "3" => Some(3)
        case "一定要" | "10000" => Some(10000)
        case _ => None
    }
}

private func resolveImage(csvPath: String, image: String): String {
    if (image.contains("\u{0}") || image.contains("://") || image.startsWith("data:") || image.startsWith("file:")) {
        throw IllegalArgumentException("请填写本地图片路径，不能填写网址或包含空字符。")
    }
    let path = Path(image.replace("\\", "/"))
    if (path.isAbsolute()) { return path.normalize().toString() }
    let parent = Path(csvPath).parent
    let base = if (parent.isEmpty()) { Path(".") } else { parent }
    base.join(path).normalize().toString()
}

/** imageCheck returns None only after the local image has been validated.
 * It is mandatory: production callers must supply the real decoder adapter.
 * This function never changes the current catalog or copies any image files.
 */
public func validateProductCsv(text: String, csvPath: String, imageCheck: (String) -> ?String): CsvReport {
    let issues = ArrayList<CsvIssue>()
    let rows = parseRows(text, issues)
    if (rows.isEmpty()) {
        issues.add(CsvIssue(1, "CSV 文件", "请提供包含表头和商品的 CSV 文件。"))
        return CsvReport([], issues.toArray(), 0, 0)
    }
    let syntaxIssueCount = issues.size
    let expected = ["商品名称", "价格", "喜欢程度", "图片路径"]
    let positions = Array<Int64>(4, {_ => -1})
    let header = rows[0]
    for (i in 0..header.cells.size) {
        let raw = header.cells[i].trimAscii()
        let name = if (raw == "名称") { "商品名称" } else { raw }
        var found = false
        for (j in 0..4) {
            if (name == expected[j]) {
                found = true
                if (positions[j] >= 0) { issues.add(CsvIssue(header.line, name, "表头重复。")) }
                else { positions[j] = i }
            }
        }
        if (!found) { issues.add(CsvIssue(header.line, "表头", "无法识别列：${raw}")) }
    }
    for (i in 0..4) {
        if (positions[i] < 0) { issues.add(CsvIssue(header.line, expected[i], "缺少此表头。")) }
    }
    if (issues.size > syntaxIssueCount) { return CsvReport([], issues.toArray(), rows.size - 1, 0) }
    let products = ArrayList<Product>()
    var unrated: Int64 = 0
    if (rows.size == 1) { issues.add(CsvIssue(header.line + 1, "商品", "CSV 中没有商品。")) }
    for (index in 1..rows.size) {
        let row = rows[index]
        if (row.cells.size != 4) {
            issues.add(CsvIssue(row.line, "列数", "每行需要四列，当前为 ${row.cells.size} 列。"))
            continue
        }
        let name = row.cells[positions[0]].trimAscii()
        let priceText = row.cells[positions[1]].trimAscii()
        let ratingText = row.cells[positions[2]].trimAscii()
        let image = row.cells[positions[3]].trimAscii()
        if (name.isEmpty() || name.contains("\u{0}")) { issues.add(CsvIssue(row.line, "商品名称", "请输入不含空字符的商品名称。")) }
        let price = parsePrice(priceText)
        if (price.isNone()) { issues.add(CsvIssue(row.line, "价格", "请输入 1 到 1000 的整数。")) }
        let rating = parseRating(ratingText)
        if (ratingText.isEmpty()) { unrated += 1 }
        else if (rating.isNone()) { issues.add(CsvIssue(row.line, "喜欢程度", "请填写五档中文或评分数字 -1、1、2、3、10000。")) }
        var imagePath = ""
        if (image.isEmpty()) { issues.add(CsvIssue(row.line, "图片路径", "请补齐本地商品图片。")) }
        else {
            try {
                imagePath = resolveImage(csvPath, image)
                match (imageCheck(imagePath)) {
                    case Some(message) => issues.add(CsvIssue(row.line, "图片路径", message))
                    case None => ()
                }
            } catch (error: Exception) {
                issues.add(CsvIssue(row.line, "图片路径", "图片检查失败：${error.message}"))
            }
        }
        products.add(Product(name, price.getOrDefault({=> 0}), rating, imagePath))
    }
    CsvReport(if (issues.isEmpty()) { products.toArray() } else { [] }, issues.toArray(), rows.size - 1, unrated)
}

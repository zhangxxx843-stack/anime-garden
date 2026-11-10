package xin_xuan_glass_probe.shopping

@When[os == "Windows"]
private func csvTestPath(path: String): String { "C:" + path }

@When[os != "Windows"]
private func csvTestPath(path: String): String { path }

private let CSV_HEADER = "商品名称,价格,喜欢程度,图片路径\n"
private func imageExists(_: String): ?String { None }

@Test
func csvAcceptsBomCrLfDuplicateNamesAndUnratedRows(): Unit {
    let report = validateProductCsv("\u{FEFF}商品名称,价格,喜欢程度,图片路径\r\n耳机,299,喜欢,images/a.jpg\r\n耳机,169,,images/b.jpg\r\n", csvTestPath("/catalog/items.csv"), imageExists)
    @Expect(report.issues.size, 0)
    @Expect(report.products.size, 2)
    @Expect(report.unratedCount, 1)
    @Expect(report.products[0].rating, Some(3))
    @Expect(report.products[1].rating, None)
    @Expect(report.products[0].imagePath.replace("\\", "/"), csvTestPath("/catalog/images/a.jpg"))
}

@Test
func csvHandlesQuotedCommasEscapesAndMultilineFields(): Unit {
    let report = validateProductCsv(CSV_HEADER + "\"耳机,\"\"轻盈\"\"\n版\",100,一定要,\"images/a,b.jpg\"\n台灯,1,一般,a.png\n", csvTestPath("/catalog/items.csv"), imageExists)
    @Expect(report.issues.size, 0)
    @Expect(report.products[0].name, "耳机,\"轻盈\"\n版")
    @Expect(report.products[0].imagePath.replace("\\", "/"), csvTestPath("/catalog/images/a,b.jpg"))
    @Expect(report.products[0].rating, Some(10000))
}

@Test
func csvAcceptsEveryChineseAndNumericRating(): Unit {
    let texts = ["不喜欢", "一般", "较喜欢", "喜欢", "一定要", "-1", "1", "2", "3", "10000"]
    let scores: Array<Int64> = [-1, 1, 2, 3, 10000, -1, 1, 2, 3, 10000]
    var csv = CSV_HEADER
    for (text in texts) { csv += "商品,1,${text},a.png\n" }
    let report = validateProductCsv(csv, csvTestPath("/data/items.csv"), imageExists)
    @Expect(report.issues.size, 0)
    for (i in 0..texts.size) { @Expect(report.products[i].rating, Some(scores[i])) }
}

@Test
func csvCollectsFieldAndImageErrorsAndBlocksWholeBatch(): Unit {
    let csv = CSV_HEADER + "好商品,5,3,ok.png\n,0,4,\n坏图片,1001,,missing.png\n"
    let report = validateProductCsv(csv, csvTestPath("/data/items.csv"), {path =>
        if (path.endsWith("missing.png")) { Some("图片不存在") } else { None }
    })
    @Expect(report.products.size, 0)
    @Expect(report.rowCount, 3)
    @Expect(report.issues.size, 6)
    @Expect(report.issues[0].line, 3)
    @Expect(report.issues[0].field, "商品名称")
    @Expect(report.issues[5].line, 4)
}

@Test
func csvSupportsReorderedHeadersNameAliasAndBackslashRelativePaths(): Unit {
    let report = validateProductCsv("图片路径,喜欢程度,名称,价格\na\\b.jpg,2,背包,1000\n", csvTestPath("/data/items.csv"), imageExists)
    @Expect(report.issues.size, 0)
    @Expect(report.products[0].price, 1000)
    @Expect(report.products[0].imagePath.replace("\\", "/"), csvTestPath("/data/a/b.jpg"))
}

@Test
func csvRejectsBadHeaderSyntaxAndColumnCounts(): Unit {
    for (text in ["", "商品名称,价格,喜欢程度,未知列\na,1,3,x\n", "商品名称,价格,价格,图片路径\n", CSV_HEADER + "\"未关闭,1,3,x\n", CSV_HEADER + "a,1,3,x,多余\n", CSV_HEADER + "\"a\"坏字符,1,3,x\n", CSV_HEADER]) {
        let report = validateProductCsv(text, csvTestPath("/data/items.csv"), imageExists)
        @Expect(report.issues.size > 0)
        @Expect(report.products.size, 0)
    }
}

@Test
func csvRejectsDecimalOverflowAndInvalidRatingButAcceptsBlankLines(): Unit {
    let text = CSV_HEADER + "\n商品,1.50,3,a.png\n商品,999999999999999999999999,3,b.png\n商品,1,5,c.png\n"
    let report = validateProductCsv(text, csvTestPath("/data/items.csv"), imageExists)
    @Expect(report.rowCount, 3)
    @Expect(report.issues.size, 3)
    @Expect(report.products.size, 0)
}

@Test
func csvRejectsUrlsAndNulAndHandlesImageCheckExceptions(): Unit {
    let invalidPaths = ["https://example.com/a.png", "a\u{0}.png"]
    for (path in invalidPaths) {
        let report = validateProductCsv(CSV_HEADER + "商品,1,3,${path}", csvTestPath("/data/items.csv"), imageExists)
        @Expect(report.products.size, 0)
        @Expect(report.issues.size, 1)
    }
    let report = validateProductCsv(CSV_HEADER + "商品,1,3,a.png", csvTestPath("/data/items.csv"), {_ => throw IllegalArgumentException("测试读取失败")})
    @Expect(report.issues.size, 1)
    @Expect(report.products.size, 0)
}

@Test
func csvRetainsAbsoluteImagePathsAndReportsPhysicalLineAfterQuotedNewline(): Unit {
    let good = validateProductCsv(CSV_HEADER + "商品,1,3,${csvTestPath("/other/a.png")}", csvTestPath("/data/items.csv"), imageExists)
    @Expect(good.products[0].imagePath.replace("\\", "/"), csvTestPath("/other/a.png"))
    let bad = validateProductCsv(CSV_HEADER + "\"商品\n一\",1,3,a.png\n商品二,0,3,b.png", csvTestPath("/data/items.csv"), imageExists)
    @Expect(bad.issues.size, 1)
    @Expect(bad.issues[0].line, 4)
}

@Test
func csvReportsRecoverableSyntaxAndLaterFieldErrorsTogether(): Unit {
    let report = validateProductCsv(CSV_HEADER + "\"商品\"意外字符,1,3,a.png\n商品二,0,4,\n", csvTestPath("/data/items.csv"), imageExists)
    @Expect(report.products.size, 0)
    @Expect(report.issues.size, 4)
    if (report.issues.size > 1) { @Expect(report.issues[1].line, 3) }
}

@Test
func csvRejectsEmbeddedNulInProductNames(): Unit {
    let report = validateProductCsv(CSV_HEADER + "商品\u{0}名称,1,3,a.png", csvTestPath("/data/items.csv"), imageExists)
    @Expect(report.products.size, 0)
    @Expect(report.issues.size, 1)
    if (!report.issues.isEmpty()) { @Expect(report.issues[0].field, "商品名称") }
}

@When[os == "Windows"]
@Test
func csvWindowsDriveAndUncPathsRemainAbsolute(): Unit {
    for (image in ["D:/商品/耳机.jpg", "//server/share/耳机.jpg"]) {
        let report = validateProductCsv(CSV_HEADER + "耳机,1,3,${image}", "C:/catalog/items.csv", imageExists)
        @Expect(report.issues.size, 0)
        if (!report.products.isEmpty()) { @Expect(report.products[0].imagePath.replace("\\", "/"), image) }
    }
}

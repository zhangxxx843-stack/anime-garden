package xin_xuan_glass_probe.importing

import xin_xuan_glass_probe.shopping.recommend

@Test
func realCsvDecodesLocalImagesAndKeepsDuplicateNames(): Unit {
    let report = readProductCsv("tests/fixtures/catalog/valid.csv")
    @Expect(report.issues.size, 0)
    @Expect(report.products.size, 2)
    @Expect(report.unratedCount, 1)
    @Expect(report.products[0].imagePath.replace("\\", "/"), "assets/headphones.jpg")
    @Expect(report.products[0].name, report.products[1].name)
}

@Test
func realCsvCollectsCorruptMissingAndDirectoryImageErrors(): Unit {
    let report = readProductCsv("tests/fixtures/catalog/bad-images.csv")
    @Expect(report.issues.size, 3)
    @Expect(report.products.size, 0)
    @Expect(report.issues[0].line, 2)
    @Expect(report.issues[1].line, 3)
    @Expect(report.issues[2].line, 4)
}

@Test
func realCsvReportsUnreadableAndInvalidUtf8Files(): Unit {
    for (path in ["tests/fixtures/catalog/no-such.csv", "tests/fixtures/catalog/invalid-utf8.csv", "tests/fixtures/catalog"]) {
        let report = readProductCsv(path)
        @Expect(report.products.size, 0)
        @Expect(report.issues.size, 1)
        @Expect(report.issues[0].line, 0)
        @Expect(report.issues[0].field, "CSV 文件")
    }
}

@Test
func importedUnratedProductsCannotBypassRatingBeforeRecommendation(): Unit {
    let report = readProductCsv("tests/fixtures/catalog/catalog.csv")
    @Expect(report.issues.size, 0)
    var rejected = false
    try { let _ = recommend(report.products, 600) }
    catch (_: IllegalArgumentException) { rejected = true }
    @Expect(rejected)
}

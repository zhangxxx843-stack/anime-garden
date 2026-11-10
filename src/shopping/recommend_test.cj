package xin_xuan_glass_probe.shopping

import std.collection.ArrayList

private func product(price: Int64, rating: Int64): Product {
    Product("商品", price, Some(rating), "image.jpg")
}

private func assertIndices(actual: Array<Int64>, expected: Array<Int64>): Unit {
    @Expect(actual.size, expected.size)
    if (actual.size == expected.size) {
        for (i in 0..actual.size) { @Expect(actual[i], expected[i]) }
    }
}

@Test
func normalReturnsThreeDifferentBudgetedCombinations(): Unit {
    let plans = recommend([product(3, 3), product(2, 2), product(4, 1), product(1, -1)], 5)
    @Expect(plans.size, 3)
    assertIndices(plans[0].indices, [0, 1])
    assertIndices(plans[1].indices, [0])
    assertIndices(plans[2].indices, [1])
    @Expect(plans[0].totalPrice, 5)
    @Expect(plans[0].totalScore, 5)
}

@Test
func equalScoresPreferLowerCostThenInputOrder(): Unit {
    let plans = recommend([product(2, 3), product(1, 3), product(1, 3), product(3, 3)], 2)
    assertIndices(plans[0].indices, [1, 2])
    assertIndices(plans[1].indices, [1])
    assertIndices(plans[2].indices, [2])
}

@Test
func tiesWithDifferentItemCountsUseIndexSequence(): Unit {
    let plans = recommend([product(1, 1), product(1, 1), product(2, 2), product(3, -1)], 2)
    assertIndices(plans[0].indices, [0, 1])
    assertIndices(plans[1].indices, [2])
}

@Test
func mustHaveIsScoreRatherThanMandatoryPurchase(): Unit {
    let plans = recommend([product(5, 10000), product(2, 10000), product(2, 10000), product(1, -1)], 5)
    assertIndices(plans[0].indices, [1, 2])
    @Expect(plans[0].totalScore, 20000)
}

@Test
func negativeRatingsStillReturnBestNonemptyChoices(): Unit {
    let plans = recommend([product(4, -1), product(1, -1), product(2, -1), product(3, -1)], 4)
    assertIndices(plans[0].indices, [1])
    assertIndices(plans[1].indices, [2])
    assertIndices(plans[2].indices, [3])
}

@Test
func boundaryDoesNotBuySameProductTwice(): Unit {
    let plans = recommend([product(1, 3), product(1000, 1), product(1000, 1), product(1000, 1)], 2)
    @Expect(plans.size, 1)
    assertIndices(plans[0].indices, [0])
    @Expect(plans[0].totalScore, 3)
    @Expect(recommend([product(1000, 3), product(1000, 2), product(1000, 1), product(1000, -1)], 1000).size, 3)
    @Expect(recommend([product(2, 1), product(2, 1), product(2, 1), product(2, 1)], 1).size, 0)
}

private func rejected(products: Array<Product>, budget: Int64): Bool {
    try { let _ = recommend(products, budget); false }
    catch (_: IllegalArgumentException) { true }
}

@Test
func invalidInputsAreRejectedBeforeCalculation(): Unit {
    let valid = [product(1, 1), product(2, 2), product(3, 3), product(4, 10000)]
    @Expect(rejected(valid, 0))
    @Expect(rejected(valid, 1001))
    @Expect(rejected([product(1, 1)], 5))
    @Expect(rejected([product(0, 1), valid[1], valid[2], valid[3]], 5))
    @Expect(rejected([product(1001, 1), valid[1], valid[2], valid[3]], 5))
    @Expect(rejected([Product("", 1, Some(1), ""), valid[1], valid[2], valid[3]], 5))
    @Expect(rejected([Product("商品", 1, None, ""), valid[1], valid[2], valid[3]], 5))
    @Expect(rejected([product(1, 4), valid[1], valid[2], valid[3]], 5))
}

// Independent exhaustive oracle: enumerate every nonempty subset, then select minima
// using tuple comparison implemented here rather than the production insertion helper.
private func oracleBefore(a: ShoppingPlan, b: ShoppingPlan): Bool {
    if (a.totalScore != b.totalScore) { return a.totalScore > b.totalScore }
    if (a.totalPrice != b.totalPrice) { return a.totalPrice < b.totalPrice }
    for (i in 0..min(a.indices.size, b.indices.size)) {
        if (a.indices[i] != b.indices[i]) { return a.indices[i] < b.indices[i] }
    }
    a.indices.size < b.indices.size
}

@Test
func dynamicProgrammingMatchesIndependentEnumeration(): Unit {
    let scores: Array<Int64> = [-1, 1, 2, 3, 10000]
    for (seed in 0..50) {
        let products = Array<Product>(7, {i => product(1 + (seed * 7 + i * 3) % 8, scores[(seed + i * 2) % 5])})
        let budget = 1 + seed % 20
        let all = ArrayList<ShoppingPlan>()
        for (mask in 1..128) {
            let chosen = ArrayList<Int64>()
            var price: Int64 = 0
            var score: Int64 = 0
            for (i in 0..7) {
                if ((mask & (1 << i)) != 0) {
                    chosen.add(i); price += products[i].price; score += products[i].rating.getOrThrow()
                }
            }
            if (price <= budget) { all.add(ShoppingPlan(chosen.toArray(), price, score)) }
        }
        let expected = ArrayList<ShoppingPlan>()
        while (expected.size < 3 && !all.isEmpty()) {
            var best: Int64 = 0
            for (i in 1..all.size) { if (oracleBefore(all[i], all[best])) { best = i } }
            expected.add(all.remove(at: best))
        }
        let actual = recommend(products, budget)
        @Expect(actual.size, expected.size)
        if (actual.size == expected.size) {
            for (i in 0..actual.size) {
                assertIndices(actual[i].indices, expected[i].indices)
                @Expect(actual[i].totalPrice, expected[i].totalPrice)
                @Expect(actual[i].totalScore, expected[i].totalScore)
            }
        }
    }
}

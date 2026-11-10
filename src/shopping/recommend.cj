package xin_xuan_glass_probe.shopping

import std.collection.ArrayList

private func validate(products: Array<Product>, budget: Int64): Unit {
    if (budget < 1 || budget > 1000) {
        throw IllegalArgumentException("预算请输入 1 到 1000 的整数。")
    }
    if (products.size <= 3) { throw IllegalArgumentException("请至少添加四件商品。") }
    for (i in 0..products.size) {
        let item = products[i]
        if (item.name.trimAscii().isEmpty()) {
            throw IllegalArgumentException("第 ${i + 1} 件商品缺少名称。")
        }
        if (item.price < 1 || item.price > 1000) {
            throw IllegalArgumentException("第 ${i + 1} 件商品的价格须为 1 到 1000 的整数。")
        }
        let rating = match (item.rating) {
            case Some(value) => value
            case None => throw IllegalArgumentException("请先选择第 ${i + 1} 件商品的喜欢程度。")
        }
        if (rating != -1 && rating != 1 && rating != 2 && rating != 3 && rating != 10000) {
            throw IllegalArgumentException("第 ${i + 1} 件商品的喜欢程度无效。")
        }
    }
}

private func before(a: ShoppingPlan, b: ShoppingPlan): Bool {
    if (a.totalScore != b.totalScore) { return a.totalScore > b.totalScore }
    if (a.totalPrice != b.totalPrice) { return a.totalPrice < b.totalPrice }
    for (i in 0..min(a.indices.size, b.indices.size)) {
        if (a.indices[i] != b.indices[i]) { return a.indices[i] < b.indices[i] }
    }
    a.indices.size < b.indices.size
}

private func retainTopThree(plans: ArrayList<ShoppingPlan>, candidate: ShoppingPlan): Unit {
    plans.add(candidate)
    var i = plans.size - 1
    while (i > 0 && before(plans[i], plans[i - 1])) {
        let previous = plans[i - 1]
        plans[i - 1] = plans[i]
        plans[i] = previous
        i -= 1
    }
    if (plans.size > 3) { plans.remove(at: plans.size - 1) }
}

/** Exact-cost 0/1 dynamic programming, retaining three distinct paths per cost.
 * Positive prices make descending updates safe. Equal-cost positive-price paths
 * cannot be proper prefixes of each other, so appending the same future indices
 * preserves their lexicographic order and pruning to three remains exact.
 * Empty paths seed the DP but are never presented as shopping recommendations.
 */
public func recommend(products: Array<Product>, budget: Int64): Array<ShoppingPlan> {
    validate(products, budget)
    let costs = Array<ArrayList<ShoppingPlan>>(budget + 1, {_ => ArrayList<ShoppingPlan>()})
    costs[0].add(ShoppingPlan([], 0, 0))
    for (index in 0..products.size) {
        let item = products[index]
        var cost = budget
        while (cost >= item.price) {
            for (previous in costs[cost - item.price]) {
                let indices = Array<Int64>(previous.indices.size + 1, {i =>
                    if (i < previous.indices.size) { previous.indices[i] } else { index }
                })
                retainTopThree(costs[cost], ShoppingPlan(indices, cost,
                    previous.totalScore + item.rating.getOrThrow()))
            }
            cost -= 1
        }
    }
    let result = ArrayList<ShoppingPlan>()
    for (cost in 1..=budget) {
        for (plan in costs[cost]) { retainTopThree(result, plan) }
    }
    result.toArray()
}

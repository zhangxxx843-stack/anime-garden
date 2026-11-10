package xin_xuan_glass_probe.application

import std.collection.ArrayList
import std.fs.Path
import xin_xuan_glass_probe.shopping.{Product, ShoppingPlan, recommend}
import xin_xuan_glass_probe.storage.{LocalStore, ShoppingSession, ShoppingState}

private func boundedInteger(text: String): ?Int64 {
    if (text.isEmpty()) { return None }
    var n: Int64 = 0
    for (byte in text.toArray()) {
        if (byte < 48 || byte > 57) { return None }
        n = n * 10 + Int64(byte - 48)
        if (n > 1000) { return None }
    }
    if (n > 0) { Some(n) } else { None }
}

public class CatalogController {
    private let session: ShoppingSession
    private let rowKeys = ArrayList<Int64>()
    private let names = ArrayList<String>()
    private let prices = ArrayList<String>()
    private var draftBudget = ""
    private var pendingDraft = false
    public var notice = ""
    public var ratingOpen = false
    public var ratingIndex: Int64 = 0
    public var showResults = false
    public var pendingDelete: ?Int64 = None
    public var plans: Array<ShoppingPlan> = []
    public prop state: ShoppingState { get() { session.state } }
    public prop keys: Array<Int64> { get() { rowKeys.toArray() } }
    public prop budgetText: String { get() { draftBudget } }
    public prop restoreWarning: String { get() { session.restoreWarning } }
    public prop saveStatus: String { get() { if (pendingDraft) { "尚未保存：请修正输入" } else { session.saveMessage } } }

    public init(store: LocalStore, assetRoot: String) {
        session = ShoppingSession(store)
        if (!session.restored && session.restoreWarning.isEmpty()) {
            let names = ["无线耳机", "阅读台灯", "运动水杯", "徒步背包", "桌面收纳盒"]
            let costs: Array<Int64> = [299, 169, 79, 259, 69]
            let images = ["headphones.jpg", "lamp.jpg", "bottle.jpg", "backpack.jpg", "organizer.jpg"]
            let products = Array<Product>(5, {i => Product(names[i], costs[i], None, Path(assetRoot).join(Path(images[i])).toString())})
            session.update(ShoppingState(None, products))
        }
        let initial = session.state
        draftBudget = match (initial.budget) { case Some(n) => "${n}"; case None => "" }
        for (i in 0..initial.products.size) {
            rowKeys.add(i); names.add(initial.products[i].name); prices.add("${initial.products[i].price}")
        }
    }

    private func index(key: Int64): ?Int64 {
        for (i in 0..rowKeys.size) { if (rowKeys[i] == key) { return Some(i) } }
        None
    }
    public func nameText(key: Int64): String { match (index(key)) { case Some(i) => names[i]; case None => "" } }
    public func priceText(key: Int64): String { match (index(key)) { case Some(i) => prices[i]; case None => "" } }
    public func editBudget(value: String): Unit {
        if (draftBudget == value) { return }
        draftBudget = value; pendingDraft = true; commitDraft()
    }
    public func editName(key: Int64, value: String): Unit {
        if (let Some(i) <- index(key)) {
            if (names[i] == value) { return }
            names[i] = value; pendingDraft = true; commitDraft()
        }
    }
    public func editPrice(key: Int64, value: String): Unit {
        if (let Some(i) <- index(key)) {
            if (prices[i] == value) { return }
            prices[i] = value; pendingDraft = true; commitDraft()
        }
    }
    private func draft(): ShoppingState {
        let budget: ?Int64 = if (draftBudget.trimAscii().isEmpty()) { None } else {
            Some(boundedInteger(draftBudget.trimAscii()).getOrThrow({=> IllegalArgumentException("预算请输入 1 到 1000 的整数。")}))
        }
        let source = session.state.products
        let products = Array<Product>(source.size, {i =>
            let name = names[i].trimAscii()
            if (name.isEmpty() || name.contains("\u{0}")) { throw IllegalArgumentException("请填写商品名称。") }
            let price = boundedInteger(prices[i].trimAscii()).getOrThrow({=> IllegalArgumentException("商品价格请输入 1 到 1000 的整数。")})
            Product(name, price, source[i].rating, source[i].imagePath)
        })
        ShoppingState(budget, products)
    }
    private func commitDraft(): Unit {
        let value = try { draft() } catch (error: Exception) {
            notice = error.message; plans = []; showResults = false; return
        }
        session.update(value)
        pendingDraft = false
        notice = if (session.unsaved) { session.saveMessage } else { "" }
        if (!plans.isEmpty()) {
            let wasShowingResults = showResults
            calculate()
            showResults = wasShowingResults && !plans.isEmpty()
        }
    }
    public func needsCloseConfirmation(): Bool { pendingDraft || session.unsaved }
    public func retryBeforeClose(): Bool {
        if (pendingDraft) { commitDraft() } else { session.retrySave() }
        if (needsCloseConfirmation()) { notice = if (pendingDraft) { notice } else { session.saveMessage } }
        !needsCloseConfirmation()
    }
    public func requestDelete(key: Int64): Unit { if (index(key).isSome()) { pendingDelete = Some(key) } }
    public func cancelDelete(): Unit { pendingDelete = None }
    public func confirmDelete(): Unit {
        if (let Some(key) <- pendingDelete) {
            if (let Some(at) <- index(key)) {
                let old = session.state
                let products = Array<Product>(old.products.size - 1, {i => old.products[if (i < at) { i } else { i + 1 }]})
                rowKeys.remove(at: at); names.remove(at: at); prices.remove(at: at)
                session.update(ShoppingState(old.budget, products))
                plans = []; showResults = false
                if (pendingDraft) { commitDraft() }
            }
        }
        pendingDelete = None
    }
    public func beginRating(): Unit {
        if (pendingDraft) { commitDraft() }
        if (pendingDraft) { return }
        if (state.budget.isNone()) { notice = "请先填写预算。"; return }
        if (state.products.size <= 3) { notice = "请至少准备四件商品后再评分。"; return }
        match (state.firstUnrated()) {
            case Some(i) => ratingIndex = i; ratingOpen = true; notice = ""
            case None => calculate()
        }
    }
    public func setRating(at: Int64, score: Int64): Unit {
        if (at < 0 || at >= state.products.size) { return }
        if (score != -1 && score != 1 && score != 2 && score != 3 && score != 10000) { return }
        let value = state
        let products = value.products.clone()
        let item = products[at]
        products[at] = Product(item.name, item.price, Some(score), item.imagePath)
        session.update(ShoppingState(value.budget, products))
        plans = []
    }
    public func previousRating(): Unit { if (ratingIndex > 0) { ratingIndex -= 1 } }
    public func nextRating(): Unit {
        if (!ratingOpen || state.products[ratingIndex].rating.isNone()) { return }
        if (ratingIndex + 1 < state.products.size) { ratingIndex += 1 }
        else { calculate() }
    }
    public func calculate(): Unit {
        if (pendingDraft) { commitDraft(); if (pendingDraft) { return } }
        try {
            let budget = state.budget.getOrThrow({=> IllegalArgumentException("请先填写预算。")})
            plans = recommend(state.products, budget)
            showResults = true; ratingOpen = false; notice = ""
        } catch (error: Exception) { notice = error.message; plans = []; showResults = false }
    }
    public func showCatalog(): Unit { showResults = false; ratingOpen = false }
}

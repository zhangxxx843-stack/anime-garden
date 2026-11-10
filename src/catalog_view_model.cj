package xin_xuan_glass_probe

import cui.*
import xin_xuan_glass_probe.application.CatalogController
import xin_xuan_glass_probe.shopping.{Product, ShoppingPlan}

struct CatalogRow {
    let key: Int64
    let item: Product
    let name: String
    let price: String
    init(key: Int64, item: Product, name: String, price: String) {
        this.key = key; this.item = item; this.name = name; this.price = price
    }
}

struct CatalogView {
    let rows: Array<CatalogRow>
    let budget: String
    let status: String
    let notice: String
    let warning: String
    let unsaved: Bool
    let ratingOpen: Bool
    let ratingIndex: Int64
    let showResults: Bool
    let plans: Array<ShoppingPlan>
    let pendingDelete: ?Int64
    let allRated: Bool
    init(model: CatalogController) {
        let state = model.state
        let keys = model.keys
        rows = Array<CatalogRow>(keys.size, {i => CatalogRow(keys[i], state.products[i], model.nameText(keys[i]), model.priceText(keys[i]))})
        budget = model.budgetText
        status = if (model.saveStatus.isEmpty()) { "本机清单" } else { model.saveStatus }
        notice = model.notice; warning = model.restoreWarning; unsaved = model.needsCloseConfirmation()
        ratingOpen = model.ratingOpen; ratingIndex = model.ratingIndex
        showResults = model.showResults; plans = model.plans; pendingDelete = model.pendingDelete
        allRated = !rows.isEmpty() && state.firstUnrated().isNone()
    }
    func row(key: Int64): ?CatalogRow {
        for (value in rows) { if (value.key == key) { return Some(value) } }
        None
    }
}

class CatalogViewModel {
    let model: CatalogController
    let view: State<CatalogView>
    let closeVisible = State<Bool>(false)
    var pendingClose: ?CloseRequest = None
    init(model: CatalogController) { this.model = model; this.view = State<CatalogView>(CatalogView(model)) }
    func change(action: () -> Unit): Unit { action(); view.value = CatalogView(model) }
    func budgetBinding(): Binding<String> {
        view.project(get: {value => value.budget}, set: {_, value => model.editBudget(value); CatalogView(model)})
    }
    func nameBinding(key: Int64): Binding<String> {
        view.project(get: {value => value.row(key).getOrThrow().name}, set: {_, value => model.editName(key, value); CatalogView(model)})
    }
    func priceBinding(key: Int64): Binding<String> {
        view.project(get: {value => value.row(key).getOrThrow().price}, set: {_, value => model.editPrice(key, value); CatalogView(model)})
    }
    func ratingBinding(): Binding<Bool> {
        view.project(get: {value => value.ratingOpen}, set: {_, value => model.ratingOpen = value; CatalogView(model)})
    }
    func deleteBinding(): Binding<Bool> {
        view.project(get: {value => value.pendingDelete.isSome()}, set: {_, _ => model.cancelDelete(); CatalogView(model)})
    }
    func requestClose(request: CloseRequest): Unit {
        if (!model.needsCloseConfirmation()) { request.accept(); return }
        pendingClose = Some(request); closeVisible.value = true
    }
    func cancelClose(): Unit {
        if (let Some(request) <- pendingClose) { request.cancel() }
        pendingClose = None; closeVisible.value = false
    }
    func discardAndClose(): Unit {
        if (let Some(request) <- pendingClose) { request.accept() }
        pendingClose = None; closeVisible.value = false
    }
    func saveAndClose(): Unit {
        change({=> if (model.retryBeforeClose()) { discardAndClose() }})
    }
}

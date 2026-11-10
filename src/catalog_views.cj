package xin_xuan_glass_probe

import cui.*

private let INK = Color.rgb(28, 59, 63)
private let GREEN = Color.rgb(32, 111, 93)

func shoppingView(vm: CatalogViewModel, materials: Backdrop): Unit {
    ZStack {
        GlassLayer(materials, background: true)
        HStack {
            ZStack {
                GlassLayer(materials)
                VStack {
                    Label("心选购物").fontSize(20.fp).bold().foregroundColor(INK)
                    Button("商品清单", {=> vm.change({=> vm.model.showCatalog()})}).key("nav-catalog")
                    Button("逐件评分", {=> vm.change({=> vm.model.beginRating()})}).key("nav-rate")
                    Button("推荐方案", {=> vm.change({=> vm.model.calculate()})}).key("nav-plans")
                    Spacer()
                    Label("选你所爱\n花得刚好").fontSize(15.fp).foregroundColor(INK)
                }.spacing(14.vp).padding(12.vp)
            }.width(116.vp)
            ScrollView {
                VStack {
                    headerView(vm, materials)
                    if (!vm.view.value.warning.isEmpty()) { Label(vm.view.value.warning).wrap().fontSize(13.fp) }
                    if (!vm.view.value.notice.isEmpty()) { Label(vm.view.value.notice).wrap().fontSize(13.fp).foregroundColor(Color.rgb(152, 61, 43)) }
                    if (vm.view.value.showResults) { resultsView(vm, materials) }
                    else { catalogView(vm, materials) }
                    Label(vm.view.value.status).wrap().fontSize(12.fp).foregroundColor(if (vm.view.value.unsaved) { Color.rgb(152, 61, 43) } else { GREEN })
                    if (vm.view.value.unsaved) {
                        Button("重试保存", {=> vm.change({=> let _ = vm.model.retryBeforeClose()})}).key("retry-save")
                    }
                }.spacing(12.vp).padding(4.vp)
            }.flex()
        }.spacing(12.vp).padding(12.vp)
        ratingView(vm, materials)
        deletionView(vm)
        closeView(vm)
    }
}

private func headerView(vm: CatalogViewModel, materials: Backdrop): Unit {
    ZStack {
        GlassLayer(materials)
        VStack {
            Label("让喜欢装进预算").fontSize(21.fp).bold().foregroundColor(INK)
            HStack {
                Label("本次预算  ¥").fontSize(14.fp)
                TextField(vm.budgetBinding(), key: "budget").placeholder("请输入预算").width(130.vp)
                Spacer()
            }.height(38.vp)
        }.spacing(10.vp).padding(16.vp)
    }.height(112.vp)
}

private func catalogView(vm: CatalogViewModel, materials: Backdrop): Unit {
    ZStack {
        GlassLayer(materials)
        VStack {
            HStack {
                Label("商品清单").fontSize(18.fp).bold()
                Spacer()
                Label("${vm.view.value.rows.size} 件商品").fontSize(12.fp)
            }.height(26.vp)
            if (vm.view.value.rows.isEmpty()) { Label("清单为空").fontSize(16.fp).height(50.vp) }
            for (row in vm.view.value.rows) {
                HStack {
                    ImageView(row.item.imagePath).size(48.vp, 48.vp).cornerRadius(9.vp)
                    VStack {
                        TextField(vm.nameBinding(row.key), key: "name-${row.key}").placeholder("商品名称")
                        Label(if (row.item.rating.isNone()) { "未评分" } else { "已评分" }).fontSize(11.fp)
                    }.spacing(2.vp).flex()
                    TextField(vm.priceBinding(row.key), key: "price-${row.key}").placeholder("价格").width(66.vp).height(38.vp)
                    Button("删除", {=> vm.change({=> vm.model.requestDelete(row.key)})}).key("delete-${row.key}").width(52.vp).height(38.vp)
                }.spacing(8.vp).height(70.vp)
            }
            Button(if (vm.view.value.allRated) { "查看三个推荐方案" } else { "继续评分" }, {=> vm.change({=> vm.model.beginRating()})})
                .role(ButtonRole.Primary).key("start-rating").height(38.vp)
        }.spacing(8.vp).padding(14.vp)
    }.height((100.0 + Float32(vm.view.value.rows.size) * 78.0))
}

private func ratingView(vm: CatalogViewModel, materials: Backdrop): Unit {
    Modal(vm.ratingBinding(), initialFocus: "next-item", dismissOnBackdrop: false) {
        ZStack {
            GlassLayer(materials)
            VStack {
                Label("${vm.view.value.ratingIndex + 1} / ${vm.view.value.rows.size}").fontSize(11.fp)
                if (vm.view.value.ratingIndex < vm.view.value.rows.size) {
                    ImageView(vm.view.value.rows[vm.view.value.ratingIndex].item.imagePath).size(64.vp, 64.vp).cornerRadius(10.vp)
                    Label(vm.view.value.rows[vm.view.value.ratingIndex].item.name).fontSize(17.fp).bold().wrap().textAlign(TextAlign.Center).height(32.vp)
                    Label("¥${vm.view.value.rows[vm.view.value.ratingIndex].item.price}").fontSize(15.fp).textAlign(TextAlign.Center)
                    Grid(3) {
                        let labels = ["不喜欢", "一般", "较喜欢", "喜欢", "一定要"]
                        let scores: Array<Int64> = [-1, 1, 2, 3, 10000]
                        for (i in 0..5) {
                            Button(labels[i], {=> vm.change({=> vm.model.setRating(vm.view.value.ratingIndex, scores[i])})})
                                .role(if (vm.view.value.rows[vm.view.value.ratingIndex].item.rating == Some(scores[i])) { ButtonRole.Primary } else { ButtonRole.Normal })
                                .key("rating-${i}").height(30.vp)
                        }
                    }.spacing(4.vp).height(64.vp)
                    HStack {
                        Button("上一件", {=> vm.change({=> vm.model.previousRating()})}).key("previous-item").enabled(vm.view.value.ratingIndex > 0)
                        Button(if (vm.view.value.ratingIndex + 1 == vm.view.value.rows.size) { "查看三个推荐方案" } else { "下一件" }, {=> vm.change({=> vm.model.nextRating()})})
                            .role(ButtonRole.Primary).key("next-item").enabled(vm.view.value.rows[vm.view.value.ratingIndex].item.rating.isSome())
                    }.spacing(8.vp).height(34.vp)
                }
            }.spacing(3.vp).padding(6.vp).height(266.vp)
        }.height(278.vp)
    }
}

private func resultsView(vm: CatalogViewModel, materials: Backdrop): Unit {
    VStack {
        Label("为你选出的购物方案").fontSize(18.fp).bold()
        if (vm.view.value.plans.isEmpty()) { Label("当前预算没有可购买的商品，可以调整预算或清单。").wrap() }
        for (i in 0..vm.view.value.plans.size) {
            ZStack {
                GlassLayer(materials)
                VStack {
                    HStack {
                        Label("方案 ${i + 1}").fontSize(17.fp).bold()
                        if (i == 0) { Label("最佳方案").fontSize(13.fp).bold().foregroundColor(GREEN) }
                        Spacer()
                    }.height(26.vp)
                    for (index in vm.view.value.plans[i].indices) {
                        HStack {
                            ImageView(vm.view.value.rows[index].item.imagePath).size(44.vp, 44.vp).cornerRadius(8.vp)
                            Label(vm.view.value.rows[index].item.name).wrap().flex()
                            Label("¥${vm.view.value.rows[index].item.price}").fontSize(14.fp)
                        }.spacing(10.vp).height(54.vp)
                    }
                    Label("合计 ¥${vm.view.value.plans[i].totalPrice}  ·  剩余 ¥${vm.model.state.budget.getOrThrow() - vm.view.value.plans[i].totalPrice}").fontSize(14.fp).bold().height(26.vp)
                }.spacing(8.vp).padding(14.vp)
            }.height((92.0 + Float32(vm.view.value.plans[i].indices.size) * 62.0))
                .border(if (i == 0) { GREEN } else { Color.rgba(255, 255, 255, 180) }, width: if (i == 0) { 2.0 } else { 1.0 }, radius: 22.vp)
        }
        Button("调整喜欢程度", {=> vm.change({=> vm.model.showResults = false; vm.model.ratingIndex = 0; vm.model.ratingOpen = !vm.model.state.products.isEmpty()})}).key("review-ratings")
    }.spacing(12.vp)
}

private func deletionView(vm: CatalogViewModel): Unit {
    Modal(vm.deleteBinding(), initialFocus: "cancel-delete", dismissOnBackdrop: false) {
        VStack {
            Label("删除这件商品？").fontSize(18.fp).bold()
            if (let Some(key) <- vm.view.value.pendingDelete) {
                if (let Some(row) <- vm.view.value.row(key)) { Label(row.item.name).wrap() }
            }
            HStack {
                Button("取消", {=> vm.change({=> vm.model.cancelDelete()})}).key("cancel-delete")
                Button("确认删除", {=> vm.change({=> vm.model.confirmDelete()})}).role(ButtonRole.Danger).key("confirm-delete")
            }.spacing(10.vp)
        }.spacing(14.vp)
    }
}

private func closeView(vm: CatalogViewModel): Unit {
    Modal(vm.closeVisible, onDismiss: Some({=> vm.cancelClose()}), initialFocus: "cancel-close", dismissOnBackdrop: false) {
        VStack {
            Label("还有尚未保存的内容").fontSize(18.fp).bold()
            Label("可以重试保存后退出，或返回清单继续处理。").wrap()
            Button("重试保存后退出", {=> vm.saveAndClose()}).role(ButtonRole.Primary).key("save-close")
            Button("放弃并退出", {=> vm.discardAndClose()}).role(ButtonRole.Danger).key("discard-close")
            Button("取消退出", {=> vm.cancelClose()}).key("cancel-close")
            if (!vm.view.value.notice.isEmpty()) { Label(vm.view.value.notice).fontSize(12.fp).wrap() }
        }.spacing(10.vp)
    }
}

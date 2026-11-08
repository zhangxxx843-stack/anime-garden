package miniproject.service

import miniproject.model.*
import miniproject.utils.*
import std.collection.*
import std.unicode.*

public struct CategoryTotal {
    public let categoryId: String
    public let amountInCents: Int64

    public init(categoryId: String, amountInCents: Int64) {
        this.categoryId = categoryId
        this.amountInCents = amountInCents
    }
}

public struct SpendingSummary {
    public let totalInCents: Int64
    public let count: Int64
    public let categoryTotals: ArrayList<CategoryTotal>

    public init(totalInCents: Int64, count: Int64, categoryTotals: ArrayList<CategoryTotal>) {
        this.totalInCents = totalInCents
        this.count = count
        this.categoryTotals = categoryTotals
    }
}

public struct BudgetStatus {
    public let hasBudget: Bool
    public let budgetInCents: Int64
    public let spentInCents: Int64
    public let remainingInCents: Int64
    public let ratioPercent: Int64
    public let cappedProgressPercent: Int64

    public init(hasBudget: Bool, budgetInCents: Int64, spentInCents: Int64, remainingInCents: Int64, ratioPercent: Int64, cappedProgressPercent: Int64) {
        this.hasBudget = hasBudget
        this.budgetInCents = budgetInCents
        this.spentInCents = spentInCents
        this.remainingInCents = remainingInCents
        this.ratioPercent = ratioPercent
        this.cappedProgressPercent = cappedProgressPercent
    }
}

public class LedgerService {
    public let state: LedgerState

    public init(state: LedgerState) {
        this.state = state
    }

    public static func inMemory(): LedgerService {
        let service = LedgerService(LedgerState())
        service.seedDefaults("2026-11-08T00:00:00")
        return service
    }

    public func seedDefaults(now: String): Unit {
        if (state.categories.size > 0) {
            return
        }
        addCategoryWithId("category-food", "餐饮", "", now)
        addCategoryWithId("category-transport", "交通", "", now)
        addCategoryWithId("category-shopping", "购物", "", now)
        addCategoryWithId("category-learning", "学习", "", now)
    }

    func addCategoryWithId(id: String, name: String, parentId: String, now: String): Unit {
        state.categories.add(Category(id, name, parentId, now, now))
    }

    public func categoryIdByName(name: String): String {
        let target = name.trim()
        for (category in state.categories) {
            if (category.name == target && category.parentId == "") {
                return category.id
            }
        }
        throw Exception("分类不存在：${name}")
    }

    public func addCategory(name: String, parentId: String, now: String): String {
        let normalized = name.trim()
        if (normalized.size == 0) {
            throw Exception("分类名称不能为空")
        }
        if (parentId != "") {
            let parentIndex = findCategoryIndex(parentId)
            if (state.categories[parentIndex].parentId != "") {
                throw Exception("分类最多支持两级")
            }
        }
        for (category in state.categories) {
            if (category.parentId == parentId && category.name == normalized) {
                throw Exception("同层级分类名称不能重复")
            }
        }
        let id = "category-${state.categories.size + 1}"
        addCategoryWithId(id, normalized, parentId, now)
        return id
    }

    public func renameCategory(id: String, name: String, now: String): Unit {
        let normalized = name.trim()
        if (normalized.size == 0) {
            throw Exception("分类名称不能为空")
        }
        let index = findCategoryIndex(id)
        for (category in state.categories) {
            if (category.id != id && category.parentId == state.categories[index].parentId && category.name == normalized) {
                throw Exception("同层级分类名称不能重复")
            }
        }
        let original = state.categories[index]
        state.categories[index] = Category(original.id, normalized, original.parentId, original.createdAt, now)
    }

    public func addExpense(amountInCents: Int64, categoryId: String, date: String, note: String, now: String): String {
        validateExpense(amountInCents, categoryId, date)
        let id = "expense-${state.expenses.size + 1}"
        state.expenses.add(Expense(id, amountInCents, categoryId, date, note, now, now))
        return id
    }

    public func updateExpense(id: String, amountInCents: Int64, categoryId: String, date: String, note: String, now: String): Unit {
        validateExpense(amountInCents, categoryId, date)
        let index = findExpenseIndex(id)
        let original = state.expenses[index]
        state.expenses[index] = Expense(original.id, amountInCents, categoryId, date, note, original.createdAt, now)
    }

    public func deleteExpense(id: String): Unit {
        state.expenses.remove(at: findExpenseIndex(id))
    }

    func validateExpense(amountInCents: Int64, categoryId: String, date: String): Unit {
        if (amountInCents <= 0) {
            throw Exception("金额必须大于 0")
        }
        findCategoryIndex(categoryId)
        if (!isValidDate(date)) {
            throw Exception("日期无效")
        }
    }

    public func setBudget(month: String, amountInCents: Int64, now: String): Unit {
        if (month.size != 7 || !isValidDate("${month}-01") || amountInCents <= 0) {
            throw Exception("预算必须是有效月份和正数")
        }
        let index = findBudgetIndex(month)
        if (index < 0) {
            state.budgets.add(MonthlyBudget(month, amountInCents, now))
        } else {
            state.budgets[index] = MonthlyBudget(month, amountInCents, now)
        }
    }

    public func summarizeDate(date: String): SpendingSummary {
        return summarize({ expense => expense.date == date })
    }

    public func summarizeMonth(month: String): SpendingSummary {
        return summarize({ expense => monthOf(expense.date) == month })
    }

    func summarize(matcher: (Expense) -> Bool): SpendingSummary {
        var total = 0
        var count: Int64 = 0
        let totals = ArrayList<CategoryTotal>()
        for (expense in state.expenses) {
            if (!matcher(expense)) {
                continue
            }
            total += expense.amountInCents
            count += 1
            var found = false
            for (index in 0..totals.size) {
                if (index >= totals.size) { break }
                if (totals[index].categoryId == expense.categoryId) {
                    let current = totals[index]
                    totals[index] = CategoryTotal(current.categoryId, current.amountInCents + expense.amountInCents)
                    found = true
                    break
                }
            }
            if (!found) {
                totals.add(CategoryTotal(expense.categoryId, expense.amountInCents))
            }
        }
        return SpendingSummary(total, count, totals)
    }

    public func budgetStatus(month: String): BudgetStatus {
        let spent = summarizeMonth(month).totalInCents
        let index = findBudgetIndex(month)
        if (index < 0) {
            return BudgetStatus(false, 0, spent, 0, 0, 0)
        }
        let budget = state.budgets[index].amountInCents
        let ratio = spent * 100 / budget
        let capped = if (ratio > 100) { 100 } else if (ratio < 0) { 0 } else { ratio }
        return BudgetStatus(true, budget, spent, budget - spent, ratio, capped)
    }

    func findCategoryIndex(id: String): Int64 {
        for (index in 0..state.categories.size) {
            if (index < state.categories.size && state.categories[index].id == id) {
                return index
            }
        }
        throw Exception("分类不存在：${id}")
    }

    func findExpenseIndex(id: String): Int64 {
        for (index in 0..state.expenses.size) {
            if (index < state.expenses.size && state.expenses[index].id == id) {
                return index
            }
        }
        throw Exception("账单不存在：${id}")
    }

    func findBudgetIndex(month: String): Int64 {
        for (index in 0..state.budgets.size) {
            if (index < state.budgets.size && state.budgets[index].month == month) {
                return index
            }
        }
        return -1
    }
}

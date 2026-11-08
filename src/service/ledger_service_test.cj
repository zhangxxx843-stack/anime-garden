package miniproject.service

import std.unittest.*
import std.unittest.testmacro.*

@Test
class LedgerServiceTest {
    @TestCase
    func rejectsDuplicateCategoryNames(): Unit {
        let ledger = LedgerService.inMemory()
        var rejected = false
        try {
            ledger.addCategory("餐饮", "", "2026-11-08T10:00:00")
        } catch (_: Exception) {
            rejected = true
        }
        @Expect(rejected, true)
    }

    @TestCase
    func calculatesExactCentsAndOverBudgetStatus(): Unit {
        let ledger = LedgerService.inMemory()
        let foodId = ledger.categoryIdByName("餐饮")
        ledger.addExpense(10, foodId, "2026-11-08", "早餐", "2026-11-08T10:00:00")
        ledger.addExpense(20, foodId, "2026-11-09", "午餐", "2026-11-09T10:00:00")
        ledger.setBudget("2026-11", 25, "2026-11-09T10:01:00")

        let summary = ledger.summarizeMonth("2026-11")
        let budget = ledger.budgetStatus("2026-11")
        @Expect(summary.totalInCents, 30)
        @Expect(summary.count, 2)
        @Expect(budget.remainingInCents, -5)
        @Expect(budget.cappedProgressPercent, 100)
    }
}

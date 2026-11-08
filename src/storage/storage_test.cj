package miniproject.storage

import miniproject.model.*
import std.unittest.*
import std.unittest.testmacro.*

@Test
class StorageCodecTest {
    @TestCase
    func roundTripsNotesAndEmptyFields(): Unit {
        let state = LedgerState()
        state.categories.add(Category("food", "餐饮", "", "2026-11-08T10:00:00", "2026-11-08T10:00:00"))
        state.expenses.add(Expense("e1", 1800, "food", "2026-11-08", "午餐\t食堂\n盖饭", "2026-11-08T10:01:00", "2026-11-08T10:01:00"))
        state.budgets.add(MonthlyBudget("2026-11", 10000, "2026-11-08T10:02:00"))

        let restored = deserializeState(serializeState(state))
        @Expect(restored.categories.size, 1)
        @Expect(restored.expenses[0].note, "午餐\t食堂\n盖饭")
        @Expect(restored.budgets[0].amountInCents, 10000)
    }
}

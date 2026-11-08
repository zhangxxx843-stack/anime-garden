package miniproject.utils

import std.unittest.*
import std.unittest.testmacro.*

@Test
class MoneyValidationTest {
    @TestCase
    func parsesExactCents(): Unit {
        @Expect(parseAmountInCents("18.00"), 1800)
        @Expect(parseAmountInCents("0.10"), 10)
        @Expect(formatAmount(3025), "30.25")
    }

    @TestCase
    func rejectsInvalidAmounts(): Unit {
        var rejected = 0
        for (input in ["", "0", "-1", "abc", "1.234"]) {
            try {
                parseAmountInCents(input)
            } catch (_: Exception) {
                rejected += 1
            }
        }
        @Expect(rejected, 5)
    }

    @TestCase
    func validatesCalendarDates(): Unit {
        @Expect(isValidDate("2026-02-28"), true)
        @Expect(isValidDate("2024-02-29"), true)
        @Expect(isValidDate("2025-02-29"), false)
        @Expect(isValidDate("2026-13-01"), false)
    }
}

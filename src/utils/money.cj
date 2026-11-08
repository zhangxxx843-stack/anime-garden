package miniproject.utils

import std.convert.*
import std.unicode.*

func isAsciiDigits(value: String): Bool {
    if (value.size == 0) {
        return false
    }
    for (byte in value.toArray()) {
        if (byte < 48 || byte > 57) {
            return false
        }
    }
    return true
}

public func parseAmountInCents(input: String): Int64 {
    let value = input.trim()
    if (value.size == 0) {
        throw Exception("金额不能为空")
    }
    let pieces = value.split(".")
    if (pieces.size > 2 || !isAsciiDigits(pieces[0])) {
        throw Exception("金额必须是正数，最多两位小数")
    }
    let whole = Int64.parse(pieces[0])
    var fractional = 0
    if (pieces.size == 2) {
        let fraction = pieces[1]
        if (fraction.size == 0 || fraction.size > 2 || !isAsciiDigits(fraction)) {
            throw Exception("金额必须是正数，最多两位小数")
        }
        fractional = Int64.parse(fraction)
        if (fraction.size == 1) {
            fractional *= 10
        }
    }
    let cents = whole * 100 + fractional
    if (cents <= 0) {
        throw Exception("金额必须大于 0")
    }
    return cents
}

public func formatAmount(cents: Int64): String {
    let sign = if (cents < 0) { "-" } else { "" }
    let absolute = if (cents < 0) { -cents } else { cents }
    let whole = absolute / 100
    let fraction = absolute % 100
    let fractionText = if (fraction < 10) { "0${fraction}" } else { "${fraction}" }
    return "${sign}${whole}.${fractionText}"
}

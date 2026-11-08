package miniproject.utils

import std.convert.*

func validDateDigits(value: String, expectedSize: Int64): Bool {
    if (value.size != expectedSize) {
        return false
    }
    for (byte in value.toArray()) {
        if (byte < 48 || byte > 57) {
            return false
        }
    }
    return true
}

public func isValidDate(value: String): Bool {
    let pieces = value.split("-")
    if (pieces.size != 3 || !validDateDigits(pieces[0], 4) || !validDateDigits(pieces[1], 2) || !validDateDigits(pieces[2], 2)) {
        return false
    }
    let year = Int64.parse(pieces[0])
    let month = Int64.parse(pieces[1])
    let day = Int64.parse(pieces[2])
    if (year < 1 || month < 1 || month > 12 || day < 1) {
        return false
    }
    let leap = (year % 400 == 0) || (year % 4 == 0 && year % 100 != 0)
    let daysInMonth = match (month) {
        case 2 => if (leap) { 29 } else { 28 }
        case 4 | 6 | 9 | 11 => 30
        case _ => 31
    }
    return day <= daysInMonth
}

public func monthOf(date: String): String {
    if (date.size < 7) {
        return ""
    }
    return date[0..6]
}

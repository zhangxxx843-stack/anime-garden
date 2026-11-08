package miniproject.storage

import miniproject.model.*
import std.convert.*
import std.fs.*

func escapeField(value: String): String {
    return value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
}

func unescapeField(value: String): String {
    return value.replace("\\r", "\r").replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
}

public func serializeState(state: LedgerState): String {
    var output = "schemaVersion\t1\n"
    for (category in state.categories) {
        output += "C\t${escapeField(category.id)}\t${escapeField(category.name)}\t${escapeField(category.parentId)}\t${escapeField(category.createdAt)}\t${escapeField(category.updatedAt)}\n"
    }
    for (expense in state.expenses) {
        output += "E\t${escapeField(expense.id)}\t${expense.amountInCents}\t${escapeField(expense.categoryId)}\t${escapeField(expense.date)}\t${escapeField(expense.note)}\t${escapeField(expense.createdAt)}\t${escapeField(expense.updatedAt)}\n"
    }
    for (budget in state.budgets) {
        output += "B\t${escapeField(budget.month)}\t${budget.amountInCents}\t${escapeField(budget.updatedAt)}\n"
    }
    return output
}

public func deserializeState(raw: String): LedgerState {
    let state = LedgerState()
    for (line in raw.lines()) {
        if (line.size == 0 || line.startsWith("schemaVersion")) {
            continue
        }
        let fields = line.split("\t")
        if (fields.size == 0) {
            continue
        }
        match (fields[0]) {
            case "C" =>
                if (fields.size != 6) { throw Exception("数据文件中的分类记录损坏") }
                state.categories.add(Category(unescapeField(fields[1]), unescapeField(fields[2]), unescapeField(fields[3]), unescapeField(fields[4]), unescapeField(fields[5])))
            case "E" =>
                if (fields.size != 8) { throw Exception("数据文件中的账单记录损坏") }
                state.expenses.add(Expense(unescapeField(fields[1]), Int64.parse(fields[2]), unescapeField(fields[3]), unescapeField(fields[4]), unescapeField(fields[5]), unescapeField(fields[6]), unescapeField(fields[7])))
            case "B" =>
                if (fields.size != 4) { throw Exception("数据文件中的预算记录损坏") }
                state.budgets.add(MonthlyBudget(unescapeField(fields[1]), Int64.parse(fields[2]), unescapeField(fields[3])))
            case _ => throw Exception("数据文件包含未知记录")
        }
    }
    return state
}

public func loadState(path: String): LedgerState {
    if (!exists(path)) {
        return LedgerState()
    }
    let bytes = File.readFrom(path)
    return deserializeState(String.fromUtf8(bytes))
}

func ensureStorageDirectory(): Unit {
    if (!exists("data")) {
        Directory.create("data", recursive: true)
    }
}

public func saveState(path: String, state: LedgerState): Unit {
    ensureStorageDirectory()
    let temporaryPath = "${path}.tmp"
    File.writeTo(temporaryPath, serializeState(state).toArray())
    rename(temporaryPath, to: path, overwrite: true)
}

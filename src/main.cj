package miniproject

import miniproject.service.*
import miniproject.storage.*
import miniproject.utils.*
import std.fs.*

const DefaultStoragePath = "data/ledger.tsv"
const DefaultTimestamp = "2026-11-08T00:00:00"

func required(args: Array<String>, index: Int64, label: String): String {
    if (index >= args.size) {
        throw Exception("缺少参数：${label}")
    }
    return args[index]
}

func loadService(path: String): LedgerService {
    let service = LedgerService(loadState(path))
    service.seedDefaults(DefaultTimestamp)
    return service
}

func saveAndReturn(path: String, service: LedgerService, message: String): String {
    saveState(path, service.state)
    return "OK\t${message}"
}

public func executeCommand(args: Array<String>, path: String): String {
    if (args.size == 0) {
        throw Exception("缺少命令")
    }
    let command = args[0]
    let service = loadService(path)
    match (command) {
        case "init" => saveAndReturn(path, service, "initialized")
        case "snapshot" =>
            if (!exists(path)) {
                saveState(path, service.state)
            }
            serializeState(service.state)
        case "add-category" =>
            let id = service.addCategory(required(args, 1, "名称"), required(args, 2, "父分类 ID"), required(args, 3, "时间"))
            saveAndReturn(path, service, id)
        case "rename-category" =>
            service.renameCategory(required(args, 1, "分类 ID"), required(args, 2, "名称"), required(args, 3, "时间"))
            saveAndReturn(path, service, "renamed")
        case "add-expense" =>
            let amount = parseAmountInCents(required(args, 1, "金额"))
            let id = service.addExpense(amount, required(args, 2, "分类 ID"), required(args, 3, "日期"), required(args, 4, "备注"), required(args, 5, "时间"))
            saveAndReturn(path, service, id)
        case "update-expense" =>
            let amount = parseAmountInCents(required(args, 2, "金额"))
            service.updateExpense(required(args, 1, "账单 ID"), amount, required(args, 3, "分类 ID"), required(args, 4, "日期"), required(args, 5, "备注"), required(args, 6, "时间"))
            saveAndReturn(path, service, "updated")
        case "delete-expense" =>
            service.deleteExpense(required(args, 1, "账单 ID"))
            saveAndReturn(path, service, "deleted")
        case "set-budget" =>
            let amount = parseAmountInCents(required(args, 2, "预算"))
            service.setBudget(required(args, 1, "月份"), amount, required(args, 3, "时间"))
            saveAndReturn(path, service, "budget-saved")
        case _ => throw Exception("未知命令：${command}")
    }
}

main(args: Array<String>): Int64 {
    try {
        println(executeCommand(args, DefaultStoragePath))
        return 0
    } catch (error: Exception) {
        println("ERROR\t${error.message}")
        return 1
    }
}

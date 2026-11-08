package miniproject.model

public struct Category {
    public let id: String
    public var name: String
    public let parentId: String
    public let createdAt: String
    public var updatedAt: String

    public init(id: String, name: String, parentId: String, createdAt: String, updatedAt: String) {
        this.id = id
        this.name = name
        this.parentId = parentId
        this.createdAt = createdAt
        this.updatedAt = updatedAt
    }
}

public struct Expense {
    public let id: String
    public let amountInCents: Int64
    public let categoryId: String
    public let date: String
    public let note: String
    public let createdAt: String
    public let updatedAt: String

    public init(id: String, amountInCents: Int64, categoryId: String, date: String, note: String, createdAt: String, updatedAt: String) {
        this.id = id
        this.amountInCents = amountInCents
        this.categoryId = categoryId
        this.date = date
        this.note = note
        this.createdAt = createdAt
        this.updatedAt = updatedAt
    }
}

public struct MonthlyBudget {
    public let month: String
    public let amountInCents: Int64
    public let updatedAt: String

    public init(month: String, amountInCents: Int64, updatedAt: String) {
        this.month = month
        this.amountInCents = amountInCents
        this.updatedAt = updatedAt
    }
}
